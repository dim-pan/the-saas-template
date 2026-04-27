"""
Subscription domain logic used by Stripe webhooks.

This module intentionally does NOT contain webhook signature verification, idempotency, or routing.
It focuses on:
- syncing subscription rows to `public.subscriptions`
- maintaining the org billing denormalized read model on `public.organizations`
- classifying plan changes (upgrade / downgrade request / downgrade immediate)
- formatting + sending subscription-related Slack notifications
"""

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict
from uuid import UUID

from stripe import Event, Subscription, SubscriptionSchedule

from app.database.organizations import OrganizationsHandler
from app.database.stripe_catalog_items import StripeCatalogItemsHandler
from app.database.subscriptions import SubscriptionsHandler
from app.database.types_autogen import (
    PublicOrganizationsUpdate,
    PublicSubscriptionsInsert,
    PublicSubscriptionsUpdate,
)
from app.stripe.client import get_stripe_client
from app.utils.logger import get_logger
from app.utils.slack import send_slack_payments_message
from supabase import Client

logger = get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def extract_price_id_from_schedule_phase(phase: SubscriptionSchedule.Phase | None) -> str | None:
    """
    Extract a Stripe price id from a subscription schedule phase.

    Observed shapes:
    - phase.items[0].price == "price_..."
    - phase.items[0].price == {"id": "price_...", ...}
    """
    if phase is None:
        return None
    items = phase.get('items')
    if not isinstance(items, list) or len(items) == 0 or items[0] is None:
        return None
    item0 = items[0]
    price = item0.get('price')
    if isinstance(price, str):
        return price if price.strip() != '' else None
    if isinstance(price, dict):
        price_id = as_str(price.get('id'))
        return price_id if price_id is not None and price_id.strip() != '' else None
    return None


def select_next_schedule_phase(
    schedule: SubscriptionSchedule | None,
) -> SubscriptionSchedule.Phase | None:
    """
    Pick the next scheduled phase (the soonest phase with start_date > now).
    """
    if schedule is None:
        return None

    phases = schedule.phases
    if phases is None or len(phases) == 0:
        return None

    now_ts = int(utc_now().timestamp())
    best_phase = None
    best_start = None
    for phase in phases:
        start_date = phase.start_date
        if start_date is None:
            continue
        start_int = int(start_date)
        if start_int <= now_ts:
            continue
        if best_start is None or start_int < best_start:
            best_start = start_int
            best_phase = phase

    if best_phase is not None:
        return best_phase

    # Fallback: if Stripe doesn't provide future phases in the way we expect,
    # pick the second phase when present.
    if len(phases) >= 2:
        return phases[1]
    return None


def stripe_unix_to_datetime(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return None


def extract_subscription_period_start_end(
    subscription: Subscription,
) -> tuple[datetime | None, datetime | None]:
    """
    Stripe subscription period timestamps vary by API shape.
    """
    start = stripe_unix_to_datetime(subscription.get('current_period_start'))
    end = stripe_unix_to_datetime(subscription.get('current_period_end'))
    if start is not None or end is not None:
        return start, end

    items = subscription.get('items')
    if items is None:
        return None, None
    data = items.get('data')
    if not isinstance(data, list) or len(data) == 0 or data[0] is None:
        return None, None

    item0 = data[0]
    start = stripe_unix_to_datetime(item0.get('current_period_start'))
    end = stripe_unix_to_datetime(item0.get('current_period_end'))
    return start, end


def extract_subscription_end_at_for_cancellation(subscription: Subscription) -> datetime | None:
    """
    Effective end timestamp for cancel-at-period-end messaging.
    """
    _start, end = extract_subscription_period_start_end(subscription)
    if end is not None:
        return end
    return stripe_unix_to_datetime(subscription.get('cancel_at'))


def format_money(amount_minor: object, currency: str | None) -> str:
    if isinstance(amount_minor, (int, float)) and currency is not None and currency.strip() != '':
        amount_major = float(amount_minor) / 100.0
        return f'{amount_major:.2f} {currency.upper()}'
    if isinstance(amount_minor, (int, float)):
        return str(int(amount_minor))
    return 'unknown'


PlanChangeDirection = Literal['upgrade', 'downgrade_request', 'downgrade_immediate', 'changed']
DowngradeKind = Literal['request', 'immediate']


class PlanChangeClassification(TypedDict, total=False):
    direction: PlanChangeDirection | None
    from_price_id: str | None
    to_price_id: str | None

    downgrade_requested: bool
    schedule_id: str | None
    scheduled_price_id: str | None
    effective_end_of_period: datetime | None

    cancel_at_period_end: bool | None
    cancellation_requested: bool
    cancellation_undone: bool
    cancellation_feedback_submitted: bool
    cancellation_feedback: str | None
    cancellation_feedback_comment: str | None


# Previous attributes apparently is hard to type, so we'll just use Any
def _extract_prev_price_id_from_previous_attributes(previous_attributes: Any) -> str | None:
    """
    Extract the previous Stripe price id from `event.data.previous_attributes`.

    Observed shapes:
    - previous_attributes.items.data[0].price.id
    - previous_attributes.items.data[0].plan.id
    - previous_attributes.plan.id
    """
    if previous_attributes is None:
        return None

    items = previous_attributes.get('items')
    if items is not None:
        data = items.get('data')
        if isinstance(data, list) and len(data) > 0 and data[0] is not None:
            item0 = data[0]
            price = item0.get('price') or item0.get('plan')
            if isinstance(price, dict):
                price_id = as_str(price.get('id'))
                return price_id if price_id is not None and price_id.strip() != '' else None

    plan = previous_attributes.get('plan')
    if isinstance(plan, dict):
        price_id = as_str(plan.get('id'))
        return price_id if price_id is not None and price_id.strip() != '' else None

    return None


def classify_plan_change(
    *,
    db: Client,
    downgrade_kind: DowngradeKind = 'immediate',
    prev_price_id: str | None = None,
    curr_price_id: str | None = None,
    event: Event | None = None,
    subscription: Subscription | None = None,
    subscription_id: str | None = None,
    assume_downgrade_request_on_unknown_new_price: bool = False,
) -> PlanChangeClassification:
    """
    Classify plan changes and subscription.updated signals.

    - Rank-based comparison uses `stripe_catalog_items.rank` via (prev_price_id, curr_price_id).
    - For `customer.subscription.updated`, pass (event, subscription) to also detect:
      - "downgrade requested" via subscription schedule attachment (reliable signal)
      - "cancellation requested" when cancel_at_period_end flips from false -> true

    Returns a dict with explicit fields so webhook handlers can branch cleanly.

    Note: This compares ranks only. Your catalog rank policy should encode how you want yearly vs
    monthly to be treated.
    """
    result: PlanChangeClassification = {
        'direction': None,
        'from_price_id': prev_price_id,
        'to_price_id': curr_price_id,
        'downgrade_requested': False,
        'schedule_id': None,
        'scheduled_price_id': None,
        'effective_end_of_period': None,
        'cancel_at_period_end': None,
        'cancellation_requested': False,
        'cancellation_undone': False,
        'cancellation_feedback_submitted': False,
        'cancellation_feedback': None,
        'cancellation_feedback_comment': None,
    }

    previous_attributes = None
    if event is not None:
        previous_attributes = event.get('data', {}).get('previous_attributes')

    if subscription is not None:
        stripe_cancel_at_period_end = subscription.get('cancel_at_period_end') is True
        cancel_at = subscription.get('cancel_at')
        cancellation_details = subscription.get('cancellation_details')
        cancellation_reason = None
        cancellation_feedback = None
        cancellation_comment = None
        if isinstance(cancellation_details, dict):
            cancellation_reason = as_str(cancellation_details.get('reason'))
            cancellation_feedback = as_str(cancellation_details.get('feedback'))
            cancellation_comment = as_str(cancellation_details.get('comment'))

        # Stripe can represent "cancel at end of period" in multiple ways (Billing Portal often sets
        # cancel_at + cancellation_details without toggling cancel_at_period_end).
        has_cancel_at = isinstance(cancel_at, (int, float))
        is_portal_cancellation = has_cancel_at or cancellation_reason == 'cancellation_requested'
        cancel_at_period_end = stripe_cancel_at_period_end or is_portal_cancellation
        result['cancel_at_period_end'] = cancel_at_period_end

        # Cancellation requested should only fire on the initial transition, not follow-up updates
        # (e.g. user adds feedback/comment in the Portal).
        cancellation_requested = False
        if stripe_cancel_at_period_end:
            prev_cancel = None
            if isinstance(previous_attributes, dict):
                prev_cancel = previous_attributes.get('cancel_at_period_end')
            if prev_cancel is not True:
                cancellation_requested = True

        if not cancellation_requested and has_cancel_at and isinstance(previous_attributes, dict):
            if 'cancel_at' in previous_attributes and previous_attributes.get('cancel_at') is None:
                cancellation_requested = True

        if (
            not cancellation_requested
            and cancellation_reason == 'cancellation_requested'
            and isinstance(previous_attributes, dict)
        ):
            prev_details = previous_attributes.get('cancellation_details')
            if isinstance(prev_details, dict) and 'reason' in prev_details:
                prev_reason = as_str(prev_details.get('reason'))
                if prev_reason != 'cancellation_requested':
                    cancellation_requested = True

        if cancellation_requested:
            result['cancellation_requested'] = True

        # Cancellation undone should only fire when it flips from "cancelling" -> not cancelling.
        cancellation_undone = False
        if not cancel_at_period_end and isinstance(previous_attributes, dict):
            # Stripe's cancel_at_period_end toggle
            if (
                'cancel_at_period_end' in previous_attributes
                and previous_attributes.get('cancel_at_period_end') is True
            ):
                cancellation_undone = True

            # Billing Portal cancel_at toggle
            if (
                'cancel_at' in previous_attributes
                and previous_attributes.get('cancel_at') is not None
            ):
                if subscription.get('cancel_at') is None:
                    cancellation_undone = True

            # Billing Portal cancellation_details.reason toggle
            if 'cancellation_details' in previous_attributes:
                prev_details = previous_attributes.get('cancellation_details')
                prev_reason = None
                if isinstance(prev_details, dict):
                    prev_reason = as_str(prev_details.get('reason'))
                if (
                    prev_reason == 'cancellation_requested'
                    and cancellation_reason != 'cancellation_requested'
                ):
                    cancellation_undone = True

        if cancellation_undone:
            result['cancellation_undone'] = True

        # Cancellation feedback: only fire when feedback is first submitted (null/empty -> non-empty).
        if isinstance(previous_attributes, dict):
            prev_details = previous_attributes.get('cancellation_details')
            prev_feedback = None
            if isinstance(prev_details, dict):
                prev_feedback = as_str(prev_details.get('feedback'))

            feedback_now = (
                cancellation_feedback.strip()
                if isinstance(cancellation_feedback, str) and cancellation_feedback.strip() != ''
                else None
            )
            feedback_prev = (
                prev_feedback.strip()
                if isinstance(prev_feedback, str) and prev_feedback.strip() != ''
                else None
            )
            if feedback_now is not None and feedback_prev is None:
                result['cancellation_feedback_submitted'] = True
                result['cancellation_feedback'] = feedback_now
                comment_now = (
                    cancellation_comment.strip()
                    if isinstance(cancellation_comment, str) and cancellation_comment.strip() != ''
                    else None
                )
                result['cancellation_feedback_comment'] = comment_now

        if curr_price_id is None:
            inferred_curr_price_id, _product_id = extract_price_product_from_subscription(
                subscription
            )
            curr_price_id = inferred_curr_price_id
            result['to_price_id'] = curr_price_id

        if prev_price_id is None and previous_attributes is not None:
            prev_price_id = _extract_prev_price_id_from_previous_attributes(previous_attributes)
            result['from_price_id'] = prev_price_id

        # Reliable downgrade-request signal: schedule is newly attached on this update.
        if downgrade_kind == 'request' and previous_attributes is not None:
            schedule_change_field_present = (
                isinstance(previous_attributes, dict) and 'schedule' in previous_attributes
            )
            if schedule_change_field_present and previous_attributes.get('schedule') is None:
                schedule_id = as_str(subscription.get('schedule'))
                if schedule_id is not None and schedule_id.strip() != '':
                    result['schedule_id'] = schedule_id
                    result['downgrade_requested'] = True
                    result['direction'] = 'downgrade_request'

                    if curr_price_id is not None:
                        result['from_price_id'] = curr_price_id

                    # Best-effort: retrieve schedule and infer the next phase's price.
                    try:
                        client = get_stripe_client()
                        schedule = client.v1.subscription_schedules.retrieve(schedule_id)
                        next_phase = select_next_schedule_phase(schedule)
                        scheduled_price_id = extract_price_id_from_schedule_phase(next_phase)
                        result['scheduled_price_id'] = scheduled_price_id
                        result['to_price_id'] = scheduled_price_id
                    except Exception:
                        logger.exception(
                            'stripe subscription schedule retrieval failed subscription_id=%s schedule_id=%s',
                            subscription_id,
                            schedule_id,
                        )

                    _start, period_end = extract_subscription_period_start_end(subscription)
                    result['effective_end_of_period'] = period_end

    if result.get('direction') is not None:
        return result

    if prev_price_id is None:
        return result

    if curr_price_id is None:
        if downgrade_kind == 'request' and assume_downgrade_request_on_unknown_new_price:
            result['direction'] = 'downgrade_request'
            result['downgrade_requested'] = True
        return result

    if prev_price_id == curr_price_id:
        return result

    catalog = StripeCatalogItemsHandler(db)
    prev_item = catalog.get_by_stripe_price_id(prev_price_id)
    curr_item = catalog.get_by_stripe_price_id(curr_price_id)
    if prev_item is None or curr_item is None:
        result['direction'] = 'changed'
        return result
    if prev_item.rank is None or curr_item.rank is None:
        result['direction'] = 'changed'
        return result
    if curr_item.rank > prev_item.rank:
        result['direction'] = 'upgrade'
        return result
    if curr_item.rank < prev_item.rank:
        # Important: "downgrade requested" is reliably detected by *schedule attachment*.
        # When the schedule later takes effect, Stripe sends another subscription.updated with the
        # *actual* lower price. That should NOT re-trigger "downgrade requested" Slack.
        if downgrade_kind == 'request':
            result['direction'] = 'changed'
            return result

        result['direction'] = 'downgrade_immediate'
        return result

    result['direction'] = 'changed'
    return result


def slack_subscription_started(
    *, organization_id: UUID, stripe_subscription_id: str, stripe_price_id: str | None
) -> None:
    send_slack_payments_message(
        text=(
            f'🟢 Subscription started\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id}\n'
            f'- price_id: {stripe_price_id or "unknown"}'
        )
    )


def slack_subscription_renewed(
    *,
    organization_id: UUID,
    stripe_subscription_id: str,
    stripe_price_id: str | None,
    amount_paid_minor: object,
    currency: str | None,
) -> None:
    send_slack_payments_message(
        text=(
            f'🔁 Subscription renewed\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id}\n'
            f'- price_id: {stripe_price_id or "unknown"}\n'
            f'- amount_paid: {format_money(amount_paid_minor, currency)}'
        )
    )


def slack_subscription_upgraded(
    *,
    organization_id: UUID,
    stripe_subscription_id: str,
    from_price_id: str,
    to_price_id: str,
) -> None:
    send_slack_payments_message(
        text=(
            f'🔼 Subscription upgraded\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id}\n'
            f'- from_price_id: {from_price_id}\n'
            f'- to_price_id: {to_price_id}'
        )
    )


def slack_subscription_updated(
    *,
    organization_id: UUID,
    stripe_subscription_id: str,
    previous_price_id: str | None,
    new_price_id: str | None,
) -> None:
    send_slack_payments_message(
        text=(
            f'🟣 Subscription updated\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id}\n'
            f'- previous_price_id: {previous_price_id or "unknown"}\n'
            f'- new_price_id: {new_price_id or "unknown"}'
        )
    )


def slack_subscription_downgrade_requested(
    *,
    organization_id: UUID,
    stripe_subscription_id: str | None,
    schedule_id: str | None,
    from_price_id: str | None,
    to_price_id: str | None,
    effective_end_of_period: datetime | None,
) -> None:
    schedule_line = f'- schedule_id: {schedule_id}\n' if schedule_id else ''
    send_slack_payments_message(
        text=(
            f'🔽 Subscription downgrade requested\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id or "unknown"}\n'
            f'{schedule_line}'
            f'- from_price_id: {from_price_id or "unknown"}\n'
            f'- to_price_id: {to_price_id or "unknown"}\n'
            f'- effective_end_of_period: {effective_end_of_period.isoformat() if effective_end_of_period is not None else "unknown"}'
        )
    )


def slack_subscription_downgraded_immediate(
    *,
    organization_id: UUID,
    stripe_subscription_id: str,
    from_price_id: str,
    to_price_id: str,
) -> None:
    send_slack_payments_message(
        text=(
            f'🔽 Subscription downgraded (immediate)\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {stripe_subscription_id}\n'
            f'- from_price_id: {from_price_id}\n'
            f'- to_price_id: {to_price_id}'
        )
    )


def compute_billing_is_paid(*, status: str, current_period_end: datetime | None) -> bool:
    status_normalized = status.strip().lower()
    # Policy:
    # - active: paid
    # - trialing: NOT paid (no free trials)
    # - past_due/unpaid: NOT paid (cut access immediately on payment failure)
    # - canceled: paid only if already in a paid-through period (current_period_end in the future)
    if status_normalized == 'active':
        return True
    if status_normalized in {'trialing', 'past_due', 'unpaid'}:
        return False
    if status_normalized == 'canceled':
        # Treat as paid if cancellation happened but the current paid period hasn't ended yet.
        if current_period_end is not None and current_period_end > utc_now():
            return True
    return False


def update_organization_billing_from_subscription(
    *,
    db: Client,
    organization_id: UUID,
    stripe_price_id: str,
    subscription_status: str,
    cancel_at_period_end: bool,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
) -> None:
    catalog = StripeCatalogItemsHandler(db)
    item = catalog.get_by_stripe_price_id(stripe_price_id)
    plan_key = item.key if item is not None else None

    is_paid = compute_billing_is_paid(
        status=subscription_status, current_period_end=current_period_end
    )
    if not is_paid:
        plan_key = None

    payload: PublicOrganizationsUpdate = {
        'billing_plan_key': plan_key,
        'billing_status': subscription_status,
        'billing_is_paid': is_paid,
        'billing_cancel_at_period_end': cancel_at_period_end,
        'billing_updated_at': utc_now(),
    }
    if current_period_start is not None:
        payload['billing_current_period_start'] = current_period_start
    if current_period_end is not None:
        payload['billing_current_period_end'] = current_period_end

    organizations = OrganizationsHandler(db)
    _ = organizations.update_item(organization_id, payload)


def update_organization_cancel_at_period_end(
    *,
    db: Client,
    organization_id: UUID,
    cancel_at_period_end: bool,
) -> None:
    payload: PublicOrganizationsUpdate = {
        'billing_cancel_at_period_end': cancel_at_period_end,
        'billing_updated_at': utc_now(),
    }
    organizations = OrganizationsHandler(db)
    _ = organizations.update_item(organization_id, payload)


def extract_price_product_from_subscription(
    subscription: Subscription,
) -> tuple[str | None, str | None]:
    items = subscription.get('items')
    if items is None:
        return None, None
    data = items.get('data')
    if not isinstance(data, list) or len(data) == 0:
        return None, None
    item0 = data[0]
    if item0 is None:
        return None, None
    price = item0.get('price') or item0.get('plan')
    if price is None:
        return None, None
    price_id = as_str(price.get('id'))
    product_id = as_str(price.get('product'))
    return price_id, product_id


def upsert_subscription_row(
    *,
    db: Client,
    organization_id: UUID,
    subscription: Subscription,
    stripe_subscription_id: str,
    stripe_customer_id: str | None,
) -> None:
    handler = SubscriptionsHandler(db, organization_id=organization_id)
    existing = handler.get_by_stripe_subscription_id(stripe_subscription_id)

    price_id, product_id = extract_price_product_from_subscription(subscription)
    if price_id is None or product_id is None:
        raise ValueError('subscription missing price/product')

    item_id = None
    items = subscription.get('items')
    if items is not None:
        data = items.get('data')
        if isinstance(data, list) and len(data) > 0 and data[0] is not None:
            item_id = as_str(data[0].get('id'))

    status = as_str(subscription.get('status')) or 'unknown'
    cancel_at_period_end = subscription.get('cancel_at_period_end') is True
    current_period_start, current_period_end = extract_subscription_period_start_end(subscription)
    trial_end = stripe_unix_to_datetime(subscription.get('trial_end'))
    ended_at = stripe_unix_to_datetime(subscription.get('ended_at'))

    update_payload: PublicSubscriptionsUpdate = {
        'stripe_subscription_item_id': item_id,
        'stripe_customer_id': stripe_customer_id,
        'stripe_price_id': price_id,
        'stripe_product_id': product_id,
        'status': status,
        'cancel_at_period_end': cancel_at_period_end,
    }
    if current_period_start is not None:
        update_payload['current_period_start'] = current_period_start
    if current_period_end is not None:
        update_payload['current_period_end'] = current_period_end
    if trial_end is not None:
        update_payload['trial_end'] = trial_end
    if ended_at is not None:
        update_payload['ended_at'] = ended_at

    if existing is None:
        insert_payload: PublicSubscriptionsInsert = {
            'organization_id': organization_id,
            'stripe_subscription_id': stripe_subscription_id,
            'stripe_subscription_item_id': item_id,
            'stripe_customer_id': stripe_customer_id,
            'stripe_price_id': price_id,
            'stripe_product_id': product_id,
            'status': status,
            'cancel_at_period_end': cancel_at_period_end,
        }
        if current_period_start is not None:
            insert_payload['current_period_start'] = current_period_start
        if current_period_end is not None:
            insert_payload['current_period_end'] = current_period_end
        if trial_end is not None:
            insert_payload['trial_end'] = trial_end
        if ended_at is not None:
            insert_payload['ended_at'] = ended_at

        _ = handler.create_item(insert_payload)
    else:
        _ = handler.update_item(existing.id, update_payload)

    update_organization_billing_from_subscription(
        db=db,
        organization_id=organization_id,
        stripe_price_id=price_id,
        subscription_status=status,
        cancel_at_period_end=cancel_at_period_end,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
    )


def sync_subscription_from_stripe(
    *,
    db: Client,
    organization_id: UUID,
    stripe_subscription_id: str,
    stripe_customer_id: str | None,
) -> None:
    client = get_stripe_client()
    subscription = client.v1.subscriptions.retrieve(stripe_subscription_id)
    upsert_subscription_row(
        db=db,
        organization_id=organization_id,
        subscription=subscription,
        stripe_subscription_id=stripe_subscription_id,
        stripe_customer_id=stripe_customer_id,
    )
