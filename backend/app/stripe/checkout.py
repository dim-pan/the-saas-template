from typing import Literal
from uuid import UUID

from stripe.params.checkout._session_create_params import (
    SessionCreateParams,
    SessionCreateParamsDiscount,
    SessionCreateParamsLineItem,
)

from app.database.types_autogen import PublicStripeCatalogItems
from app.stripe.client import get_stripe_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_checkout_session(
    *,
    organization_id: UUID,
    stripe_customer_id: str,
    catalog_item: PublicStripeCatalogItems,
    success_url: str,
    cancel_url: str,
    actor_user_id: UUID,
) -> dict[str, str]:
    billing_type = catalog_item.billing_type.strip().lower()
    if billing_type not in {'subscription', 'one_off'}:
        raise ValueError(f'Unsupported billing_type: {catalog_item.billing_type}')

    mode: Literal['subscription', 'payment'] = (
        'subscription' if billing_type == 'subscription' else 'payment'
    )
    coupon_id = catalog_item.override_stripe_coupon_id or catalog_item.default_stripe_coupon_id

    line_items: list[SessionCreateParamsLineItem] = [
        {
            'price': catalog_item.stripe_price_id,
            'quantity': 1,
        }
    ]
    params: SessionCreateParams = {
        'mode': mode,
        'customer': stripe_customer_id,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'line_items': line_items,
        'metadata': {
            'organization_id': str(organization_id),
            'catalog_key': catalog_item.key,
            'billing_type': billing_type,
            'actor_user_id': str(actor_user_id),
        },
    }

    if isinstance(coupon_id, str) and coupon_id.strip() != '':
        discounts: list[SessionCreateParamsDiscount] = [{'coupon': coupon_id}]
        params['discounts'] = discounts
    else:
        # Allow promo codes when no explicit coupon is enforced for this item.
        params['allow_promotion_codes'] = True

    client = get_stripe_client()
    session = client.v1.checkout.sessions.create(params)
    session_id = session.id
    session_url = session.url
    if not isinstance(session_id, str) or session_id.strip() == '':
        logger.warning('stripe checkout session missing id')
        raise ValueError('Stripe checkout session creation failed (missing id)')
    if not isinstance(session_url, str) or session_url.strip() == '':
        logger.warning('stripe checkout session missing url session_id=%s', session_id)
        raise ValueError('Stripe checkout session creation failed (missing url)')

    return {'id': session_id, 'url': session_url}
