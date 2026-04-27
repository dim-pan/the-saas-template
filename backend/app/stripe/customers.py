"""
Stripe customer helpers.
"""

from dataclasses import dataclass
from uuid import UUID

import stripe

from app.stripe.client import get_stripe_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class StripeCustomerResolution:
    stripe_customer_id: str
    is_new: bool


def create_stripe_customer(*, organization_id: UUID, name: str, email: str) -> str:
    client = get_stripe_client()
    customer = client.v1.customers.create(
        {
            'name': name,
            'email': email,
            'metadata': {'organization_id': str(organization_id)},
        }
    )
    customer_id = customer.id
    if not customer_id or customer_id.strip() == '':
        raise ValueError('Stripe customer creation failed (missing customer id)')
    return customer_id


def get_or_create_stripe_customer(
    *,
    existing_customer_id: str | None,
    organization_id: UUID,
    name: str,
    email: str,
) -> StripeCustomerResolution:
    existing_id = existing_customer_id.strip() if existing_customer_id is not None else ''
    if existing_id != '':
        client = get_stripe_client()
        try:
            customer = client.v1.customers.retrieve(existing_id)
            deleted = customer.get('deleted')
            if deleted is True:
                raise ValueError(f'Stripe customer id is deleted: {existing_id}')
            return StripeCustomerResolution(stripe_customer_id=existing_id, is_new=False)
        except stripe.StripeError as exc:
            logger.warning(
                'stripe customer retrieve failed customer_id=%s: %s', existing_id, str(exc)
            )
            raise
        except Exception as exc:
            logger.warning(
                'stripe customer retrieve failed customer_id=%s: %s', existing_id, str(exc)
            )
            raise

    customer_id = create_stripe_customer(organization_id=organization_id, name=name, email=email)
    return StripeCustomerResolution(stripe_customer_id=customer_id, is_new=True)
