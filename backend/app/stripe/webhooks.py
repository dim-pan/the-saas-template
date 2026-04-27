"""
Stripe webhooks utilities.

Intended responsibilities (no implementation yet):
- Verify webhook signature (Stripe-Signature header)
- Parse incoming event payloads
- Extract org mapping keys (e.g., stripe_customer_id / subscription id)
- Idempotency helpers (optional event table later)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

import stripe

from app.config import STRIPE_WEBHOOK_SECRET
from app.database.organizations import OrganizationsHandler
from app.database.stripe_webhook_events import StripeWebhookEventsHandler
from app.database.subscriptions import SubscriptionsHandler
from app.database.types_autogen import (
    PublicStripeWebhookEvents,
    PublicStripeWebhookEventsInsert,
    PublicSubscriptionsUpdate,
)
from app.stripe.subscriptions import (
    classify_plan_change,
    extract_subscription_end_at_for_cancellation,
    format_money,
    slack_subscription_downgrade_requested,
    slack_subscription_downgraded_immediate,
    slack_subscription_renewed,
    slack_subscription_started,
    slack_subscription_updated,
    slack_subscription_upgraded,
    sync_subscription_from_stripe,
    update_organization_cancel_at_period_end,
    upsert_subscription_row,
)
from app.utils.logger import get_logger
from app.utils.slack import send_slack_payments_message
from supabase import Client

logger = get_logger(__name__)


@dataclass(frozen=True)
class StripeWebhookSummary:
    event_id: str | None
    event_type: str | None
    livemode: bool | None
    object_type: str | None
    stripe_customer_id: str | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def handle_customer_subscription_event(
    *, db: Client, event: stripe.Event, organization_id: UUID | None
) -> None:
    """
    Handles events with type prefix: customer.subscription.*
    """
    if organization_id is None:
        raise ValueError('organization_id is required for subscription events')

    event_type = event.get('type')
    if event_type == 'customer.subscription.deleted':
        _handle_customer_subscription_deleted(db=db, event=event, organization_id=organization_id)
        return
    _handle_customer_subscription_updated(db=db, event=event, organization_id=organization_id)


def handle_invoice_payment_succeeded(
    *, db: Client, event: stripe.Event, organization_id: UUID | None
) -> None:
    if organization_id is None:
        raise ValueError('organization_id is required for invoice events')
    invoice = _require_invoice(event)
    billing_reason = _as_str(invoice.get('billing_reason'))
    subscription_id = _extract_subscription_id_from_invoice(invoice)
    customer_id = _as_str(invoice.get('customer'))

    if subscription_id is None:
        # One-off invoices may not have a subscription; don't treat as subscription billing.
        return

    action = _classify_invoice_billing_reason(billing_reason)
    detected_plan = _detect_plan_from_invoice(invoice=invoice)

    new_price_id = _invoice_detected_price_id(detected_plan)
    subscription_handler = SubscriptionsHandler(db, organization_id=organization_id)

    if action == 'subscription_create':
        slack_subscription_started(
            organization_id=organization_id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=new_price_id,
        )
    elif action == 'subscription_cycle':
        existing = subscription_handler.get_by_stripe_subscription_id(subscription_id)
        price_id_for_message = new_price_id or (
            existing.stripe_price_id if existing is not None else None
        )
        amount_paid = invoice.get('amount_paid')
        currency = _as_str(invoice.get('currency'))
        slack_subscription_renewed(
            organization_id=organization_id,
            stripe_subscription_id=subscription_id,
            stripe_price_id=price_id_for_message,
            amount_paid_minor=amount_paid,
            currency=currency,
        )
    elif action == 'subscription_update':
        existing = subscription_handler.get_by_stripe_subscription_id(subscription_id)
        previous_price_id = existing.stripe_price_id if existing is not None else None

        if (
            previous_price_id is None
            or new_price_id is None
            or previous_price_id.strip() == ''
            or new_price_id.strip() == ''
            or previous_price_id == new_price_id
        ):
            slack_subscription_updated(
                organization_id=organization_id,
                stripe_subscription_id=subscription_id,
                previous_price_id=previous_price_id,
                new_price_id=new_price_id,
            )
        else:
            # Reuse the same rank-based classifier as subscription.updated, but treat invoice success
            # as the source of truth for *upgrades* (requires immediate payment).
            change = classify_plan_change(
                db=db,
                downgrade_kind='immediate',
                prev_price_id=previous_price_id,
                curr_price_id=new_price_id,
            )
            change_direction = change.get('direction')

            if change_direction == 'upgrade':
                slack_subscription_upgraded(
                    organization_id=organization_id,
                    stripe_subscription_id=subscription_id,
                    from_price_id=previous_price_id,
                    to_price_id=new_price_id,
                )
            elif change_direction == 'downgrade_immediate':
                slack_subscription_downgraded_immediate(
                    organization_id=organization_id,
                    stripe_subscription_id=subscription_id,
                    from_price_id=previous_price_id,
                    to_price_id=new_price_id,
                )
            else:
                slack_subscription_updated(
                    organization_id=organization_id,
                    stripe_subscription_id=subscription_id,
                    previous_price_id=previous_price_id,
                    new_price_id=new_price_id,
                )

    sync_subscription_from_stripe(
        db=db,
        organization_id=organization_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )


def handle_invoice_payment_failed(
    *, db: Client, event: stripe.Event, organization_id: UUID | None
) -> None:
    if organization_id is None:
        raise ValueError('organization_id is required for invoice events')
    invoice = _require_invoice(event)
    subscription_id = _extract_subscription_id_from_invoice(invoice)
    customer_id = _as_str(invoice.get('customer'))

    if subscription_id is None:
        return

    sync_subscription_from_stripe(
        db=db,
        organization_id=organization_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id,
    )


def handle_checkout_session_completed(*, event: stripe.Event, organization_id: UUID | None) -> None:
    session = event['data']['object']
    session_id = _as_str(session.get('id'))
    mode = _as_str(session.get('mode'))
    metadata = session.get('metadata')

    catalog_key = None

    if metadata is not None:
        catalog_key = _as_str(metadata.get('catalog_key'))

    # Important: do not fulfill subscriptions here; rely on invoice.payment_succeeded.
    if mode == 'subscription':
        return
    payment_status = _as_str(session.get('payment_status'))
    amount_total_minor = session.get('amount_total')
    currency = _as_str(session.get('currency'))
    if payment_status == 'paid':
        send_slack_payments_message(
            text=(
                f'✅ One-off payment received\n'
                f'- org_id: {str(organization_id) if organization_id is not None else "unknown"}\n'
                f'- session_id: {session_id or "unknown"}\n'
                f'- catalog_key: {catalog_key or "unknown"}\n'
                f'- amount: {format_money(amount_total_minor, currency)}'
            )
        )
    # TODO: for one_off payments you may want to grant entitlements here


def _classify_invoice_billing_reason(billing_reason: str | None) -> str:
    if billing_reason == 'subscription_create':
        return 'subscription_create'
    if billing_reason == 'subscription_cycle':
        return 'subscription_cycle'
    if billing_reason == 'subscription_update':
        return 'subscription_update'
    return 'unknown'


def _require_invoice(event: stripe.Event) -> stripe.Invoice:
    obj = event['data']['object']
    if not isinstance(obj, stripe.Invoice):
        raise ValueError(f'expected Stripe Invoice data.object but got: {type(obj)}')
    return obj


def _require_subscription(event: stripe.Event) -> stripe.Subscription:
    obj = event['data']['object']
    if not isinstance(obj, stripe.Subscription):
        raise ValueError(f'expected Stripe Subscription data.object but got: {type(obj)}')
    return obj


def _extract_subscription_id_from_invoice(invoice: stripe.Invoice) -> str | None:
    """
    Stripe invoices can represent the subscription in multiple shapes depending on API version.

    Observed shapes:
    - invoice.subscription
    - invoice.parent.subscription_details.subscription
    - invoice.lines.data[*].parent.subscription_item_details.subscription
    """
    direct = _as_str(invoice.get('subscription'))
    if direct is not None and direct.strip() != '':
        return direct

    parent = invoice.get('parent')
    if parent is not None:
        subscription_details = parent.get('subscription_details')
        if subscription_details is not None:
            nested = _as_str(subscription_details.get('subscription'))
            if nested is not None and nested.strip() != '':
                return nested

    lines = invoice.get('lines')
    if lines is None:
        return None
    lines_data = lines.get('data')
    if not isinstance(lines_data, list):
        return None

    for line in lines_data:
        if line is None:
            continue
        line_parent = line.get('parent')
        if line_parent is None:
            continue
        item_details = line_parent.get('subscription_item_details')
        if item_details is None:
            continue
        line_sub = _as_str(item_details.get('subscription'))
        if line_sub is not None and line_sub.strip() != '':
            return line_sub

    return None


def _detect_plan_from_invoice(*, invoice: stripe.Invoice) -> dict[str, str] | None:
    """
    Detect which plan/price the invoice is primarily charging for.

    If billing_reason is subscription_update, prefer the positive proration line as the "new plan".
    """
    billing_reason = _as_str(invoice.get('billing_reason'))

    lines = invoice.get('lines')
    if lines is None:
        return None
    lines_data = lines.get('data')
    if not isinstance(lines_data, list) or len(lines_data) == 0:
        return None

    selected_line = None
    if billing_reason == 'subscription_update':
        for line in lines_data:
            if line is None:
                continue
            is_proration = False
            parent = line.get('parent')
            if parent is not None:
                details = parent.get('subscription_item_details')
                if details is not None:
                    is_proration = details.get('proration') is True
            amount = line.get('amount')
            if is_proration and isinstance(amount, (int, float)) and amount > 0:
                selected_line = line
                break

    if selected_line is None:
        for line in lines_data:
            if line is None:
                continue
            if line.get('type') == 'subscription':
                selected_line = line
                break
        if selected_line is None:
            selected_line = lines_data[0]

    price_id, product_id = _extract_price_product_from_invoice_line(selected_line)
    if price_id is None and product_id is None:
        return None

    change = None
    if billing_reason == 'subscription_update':
        change = 'update'

    return {
        'price_id': price_id or '',
        'product_id': product_id or '',
        'change': change or '',
    }


def _extract_price_product_from_invoice_line(
    line: stripe.InvoiceLineItem,
) -> tuple[str | None, str | None]:
    # New-ish nested structure
    pricing = line.get('pricing')
    if pricing is not None:
        price_details = pricing.get('price_details')
        if price_details is not None:
            price_id = _as_str(price_details.get('price'))
            product_id = _as_str(price_details.get('product'))
            if price_id is not None or product_id is not None:
                return price_id, product_id

    price = line.get('price')
    if price is not None:
        price_id = _as_str(price.get('id'))
        product_id = _as_str(price.get('product'))
        return price_id, product_id

    plan = line.get('plan')
    if plan is not None:
        price_id = _as_str(plan.get('id'))
        product_id = _as_str(plan.get('product'))
        return price_id, product_id

    return None, None


def _handle_customer_subscription_updated(
    *, db: Client, event: stripe.Event, organization_id: UUID
) -> None:
    subscription = _require_subscription(event)
    subscription_id = _as_str(subscription.get('id'))

    classification = classify_plan_change(
        db=db,
        downgrade_kind='request',
        event=event,
        subscription=subscription,
        subscription_id=subscription_id,
    )

    # Keep org read model responsive for the UI. Billing Portal cancellations can set `cancel_at`
    # without toggling cancel_at_period_end, so use the classifier's effective value.
    update_organization_cancel_at_period_end(
        db=db,
        organization_id=organization_id,
        cancel_at_period_end=classification.get('cancel_at_period_end') is True,
    )

    # Persist cancel request state onto the subscription row (request time + undo).
    if subscription_id is not None:
        subscriptions = SubscriptionsHandler(db, organization_id=organization_id)
        existing = subscriptions.get_by_stripe_subscription_id(subscription_id)
        if existing is None:
            logger.warning(
                'stripe customer.subscription.updated missing subscription row subscription_id=%s org_id=%s',
                subscription_id,
                str(organization_id),
            )
        else:
            # NOTE: `PublicSubscriptionsUpdate` currently types `cancel_request_at` as `datetime`
            # (non-null), but the DB field is nullable (and we do set it to null on undo). Keep the
            # payload structurally correct and cast at the call site.
            update_payload: dict[str, object] = {
                'cancel_at_period_end': classification.get('cancel_at_period_end') is True,
            }
            if classification.get('cancellation_requested'):
                update_payload['cancel_request_at'] = _utc_now()
            elif classification.get('cancellation_undone'):
                update_payload['cancel_request_at'] = None
            _ = subscriptions.update_item(
                existing.id, cast(PublicSubscriptionsUpdate, update_payload)
            )

    if classification.get('direction') == 'downgrade_request':
        slack_subscription_downgrade_requested(
            organization_id=organization_id,
            stripe_subscription_id=subscription_id,
            schedule_id=classification.get('schedule_id'),
            from_price_id=classification.get('from_price_id'),
            to_price_id=classification.get('to_price_id'),
            effective_end_of_period=classification.get('effective_end_of_period'),
        )

    # Slack notify cancellation request when toggled on.
    if classification.get('cancellation_requested'):
        period_end = extract_subscription_end_at_for_cancellation(subscription)
        send_slack_payments_message(
            text=(
                f'🟠 Subscription cancellation requested\n'
                f'- org_id: {str(organization_id)}\n'
                f'- subscription_id: {subscription_id or "unknown"}\n'
                f'- ends_at: {period_end.isoformat() if period_end is not None else "unknown"}'
            )
        )

    if classification.get('cancellation_feedback_submitted'):
        feedback = classification.get('cancellation_feedback')
        comment = classification.get('cancellation_feedback_comment')
        comment_line = ''
        if feedback == 'other' and comment is not None and comment.strip() != '':
            comment_line = f'\n- comment: {comment}'
        send_slack_payments_message(
            text=(
                f'📝 Cancellation feedback\n'
                f'- org_id: {str(organization_id)}\n'
                f'- subscription_id: {subscription_id or "unknown"}\n'
                f'- feedback: {feedback or "unknown"}{comment_line}'
            )
        )

    if classification.get('cancellation_undone'):
        send_slack_payments_message(
            text=(
                f'🟢 Subscription cancellation undone\n'
                f'- org_id: {str(organization_id)}\n'
                f'- subscription_id: {subscription_id or "unknown"}'
            )
        )


def _handle_customer_subscription_deleted(
    *, db: Client, event: stripe.Event, organization_id: UUID
) -> None:
    subscription = _require_subscription(event)
    subscription_id = _as_str(subscription.get('id'))
    status = _as_str(subscription.get('status'))

    send_slack_payments_message(
        text=(
            f'⛔ Subscription ended\n'
            f'- org_id: {str(organization_id)}\n'
            f'- subscription_id: {subscription_id or "unknown"}\n'
            f'- status: {status or "unknown"}'
        )
    )
    if subscription_id is None:
        return
    upsert_subscription_row(
        db=db,
        organization_id=organization_id,
        subscription=subscription,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=_as_str(subscription.get('customer')),
    )


# TODO: Add app specific logic here


def _invoice_detected_price_id(detected_plan: dict[str, str] | None) -> str | None:
    if detected_plan is None:
        return None
    price_id = detected_plan.get('price_id')
    return price_id if isinstance(price_id, str) and price_id.strip() != '' else None


def construct_event(*, payload: bytes, signature: str) -> stripe.Event:
    if STRIPE_WEBHOOK_SECRET is None or STRIPE_WEBHOOK_SECRET.strip() == '':
        raise ValueError('STRIPE_WEBHOOK_SECRET is not configured')
    if signature.strip() == '':
        raise ValueError('Missing Stripe-Signature header')

    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        raise ValueError('Invalid Stripe webhook payload/signature') from exc


def summarize_event(event: stripe.Event) -> StripeWebhookSummary:
    try:
        event_id = event['id']
        event_type = event['type']
        livemode = event['livemode']
        data = event['data']
        stripe_object = data['object']
    except Exception as exc:
        raise ValueError('Stripe event missing required fields') from exc

    object_type = None
    stripe_customer_id = None
    object_type = stripe_object.get('object')
    stripe_customer_id = stripe_object.get('customer')

    return StripeWebhookSummary(
        event_id=_as_str(event_id),
        event_type=_as_str(event_type),
        livemode=_as_bool(livemode),
        object_type=_as_str(object_type),
        stripe_customer_id=_as_str(stripe_customer_id),
    )


def event_to_json_dict(event: stripe.Event) -> dict[str, object]:
    """
    Convert a verified Stripe Event to a JSON-serializable dict.

    Avoid StripeObject.to_dict()/to_dict_recursive() since they're deprecated.
    """
    # stripe.Event is a StripeObject (dict subclass). `dict(event)` is safe and
    # JSON-serializable (nested StripeObjects are also dict-like).
    return dict(event)


def _find_existing_event(
    handler: StripeWebhookEventsHandler, *, stripe_event_id: str
) -> PublicStripeWebhookEvents | None:
    return handler.get_by_stripe_event_id(stripe_event_id)


def get_or_create_webhook_event_row(
    *,
    db: Client,
    summary: StripeWebhookSummary,
    event_json: dict[str, object],
) -> tuple[PublicStripeWebhookEvents | None, bool]:
    """
    Ensure we have a row for this Stripe event (idempotency).

    Returns: (row_or_none, created_bool)
    """
    event_id = summary.event_id
    event_type = summary.event_type
    livemode = summary.livemode
    if event_id is None or event_type is None or livemode is None:
        logger.warning('stripe webhook missing required summary fields: %s', str(summary))
        return None, False

    handler = StripeWebhookEventsHandler(db)
    existing = _find_existing_event(handler, stripe_event_id=event_id)
    if existing is not None:
        return existing, False

    insert_payload: PublicStripeWebhookEventsInsert = {
        'stripe_event_id': event_id,
        'type': event_type,
        'livemode': livemode,
        'payload': event_json,
        'received_at': _utc_now(),
    }
    if summary.stripe_customer_id is not None:
        insert_payload['stripe_customer_id'] = summary.stripe_customer_id

    created = handler.create_item(insert_payload)
    return created, True


def resolve_organization_id(
    *,
    db: Client,
    event: stripe.Event,
    summary: StripeWebhookSummary,
    row: PublicStripeWebhookEvents,
) -> UUID | None:
    """
    Resolve org context for this webhook event.

    Priority:
    - event.data.object.metadata.organization_id (we set this on checkout sessions / customers)
    - organizations.stripe_customer_id lookup (we set this when creating the customer)
    """
    if row.organization_id is not None:
        return None

    try:
        stripe_object = event['data']['object']
    except Exception as exc:
        raise ValueError('Stripe event missing required data.object') from exc

    metadata = stripe_object.get('metadata')

    org_id_str = None
    if metadata is not None:
        org_id_str = metadata.get('organization_id')
    org_id = _as_str(org_id_str)
    if org_id is not None and org_id.strip() != '':
        try:
            return UUID(org_id)
        except ValueError:
            logger.warning('stripe webhook invalid organization_id in metadata: %s', org_id)

    stripe_customer_id = summary.stripe_customer_id
    if stripe_customer_id is not None and stripe_customer_id.strip() != '':
        org = OrganizationsHandler(db).get_by_stripe_customer_id(stripe_customer_id)
        if org is not None:
            return org.id

    logger.warning(
        'stripe webhook could not resolve organization_id event_id=%s type=%s stripe_customer_id=%s',
        summary.event_id,
        summary.event_type,
        summary.stripe_customer_id,
    )
    return None


def should_process_event(row: PublicStripeWebhookEvents) -> bool:
    """
    True idempotency:
    - If processed_at is set and processing_error is null => do not reprocess.
    - If processing_error is set (even if processed_at is null) => allow retry.
    - If processed_at is null => process.
    """
    if row.processed_at is not None and row.processing_error is None:
        return False
    return True


def mark_event_processed(*, db: Client, row_id: UUID) -> None:
    handler = StripeWebhookEventsHandler(db)
    _ = handler.update_item_status(row_id, processing_error=None)


def mark_event_failed(*, db: Client, row_id: UUID, error_message: str) -> None:
    handler = StripeWebhookEventsHandler(db)
    _ = handler.update_item_status(row_id, processing_error=error_message)
