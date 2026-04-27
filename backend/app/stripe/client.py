from functools import lru_cache
from stripe import StripeClient
from app.config import STRIPE_SECRET_KEY


@lru_cache(maxsize=1)
def get_stripe_client() -> StripeClient:
    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.strip() == '':
        raise ValueError('STRIPE_SECRET_KEY is not configured')

    return StripeClient(STRIPE_SECRET_KEY)
