from decimal import Decimal
from typing import Any

from app.database.types_autogen import PublicStripeCatalogItems
from app.stripe.client import get_stripe_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def format_money(*, amount_minor: int, currency: str) -> str:
    currency_normalized = currency.lower().strip()
    amount_major = Decimal(amount_minor) / Decimal(100)

    if currency_normalized == 'usd':
        rendered = f'{amount_major:.2f}'
        rendered = rendered.rstrip('0').rstrip('.')
        return f'${rendered}'

    rendered = f'{amount_major:.2f}'
    rendered = rendered.rstrip('0').rstrip('.')
    return f'{currency.upper()} {rendered}'


def price_unit_amount_minor(price_dict: dict[str, object]) -> int | None:
    unit_amount = price_dict.get('unit_amount')
    if isinstance(unit_amount, int):
        return unit_amount

    unit_amount_decimal = price_dict.get('unit_amount_decimal')
    if isinstance(unit_amount_decimal, str) and unit_amount_decimal.strip() != '':
        try:
            return int(Decimal(unit_amount_decimal))
        except Exception:
            return None
    return None


def price_display_suffix(price_dict: dict[str, object]) -> str:
    recurring = price_dict.get('recurring')
    if not isinstance(recurring, dict):
        return ''

    interval = recurring.get('interval')
    interval_count = recurring.get('interval_count')
    if not isinstance(interval, str) or interval.strip() == '':
        return ''
    if not isinstance(interval_count, int) or interval_count <= 0:
        interval_count = 1

    interval_normalized = interval.strip().lower()
    if interval_count == 1 and interval_normalized == 'month':
        return '/mo'
    if interval_count == 1 and interval_normalized == 'year':
        return '/yr'
    plural = 's' if interval_count != 1 else ''
    return f'/{interval_count} {interval_normalized}{plural}'


def compute_discounted_amount_minor(
    *,
    amount_minor: int,
    currency: str,
    coupon_dict: dict[str, object],
) -> int | None:
    valid = coupon_dict.get('valid')
    if valid is not True:
        return None

    percent_off = coupon_dict.get('percent_off')
    if isinstance(percent_off, (int, float)):
        discounted = (
            Decimal(amount_minor) * (Decimal(100) - Decimal(str(percent_off))) / Decimal(100)
        )
        discounted_minor = int(discounted.quantize(Decimal('1')))
        return max(discounted_minor, 0)

    amount_off = coupon_dict.get('amount_off')
    coupon_currency = coupon_dict.get('currency')
    if isinstance(amount_off, int) and amount_off >= 0:
        if coupon_currency is not None and isinstance(coupon_currency, str):
            if coupon_currency.lower().strip() != currency.lower().strip():
                return None
        return max(amount_minor - amount_off, 0)

    return None


def enrich_catalog_items_with_display_prices(
    items: list[PublicStripeCatalogItems],
) -> list[dict[str, object]]:
    stripe_client = get_stripe_client()
    price_cache: dict[str, dict[str, object]] = {}
    coupon_cache: dict[str, dict[str, object]] = {}

    enriched: list[dict[str, object]] = []
    for item in items:
        display_price: str | None = None
        display_price_discounted: str | None = None

        price_id = item.stripe_price_id
        price_dict = price_cache.get(price_id)
        if price_dict is None:
            try:
                price = stripe_client.v1.prices.retrieve(price_id)
                # Stripe objects behave like mappings; avoid deprecated to_dict_recursive().
                price_dict = dict[str, Any](price)
                price_cache[price_id] = price_dict
            except Exception as exc:
                logger.warning(
                    'stripe catalog: failed to retrieve price_id=%s: %s', price_id, str(exc)
                )
                price_dict = None

        if price_dict is not None:
            currency_obj = price_dict.get('currency')
            currency = currency_obj if isinstance(currency_obj, str) else 'usd'
            amount_minor = price_unit_amount_minor(price_dict)
            if amount_minor is not None:
                suffix = price_display_suffix(price_dict)
                display_price = (
                    f'{format_money(amount_minor=amount_minor, currency=currency)}{suffix}'
                )

                coupon_id = item.override_stripe_coupon_id or item.default_stripe_coupon_id
                if coupon_id is not None and coupon_id.strip() != '':
                    coupon_dict = coupon_cache.get(coupon_id)
                    if coupon_dict is None:
                        try:
                            coupon = stripe_client.v1.coupons.retrieve(coupon_id)
                            # Stripe objects behave like mappings; avoid deprecated to_dict_recursive().
                            coupon_dict = dict[str, Any](coupon)
                            coupon_cache[coupon_id] = coupon_dict
                        except Exception as exc:
                            logger.warning(
                                'stripe catalog: failed to retrieve coupon_id=%s: %s',
                                coupon_id,
                                str(exc),
                            )
                            coupon_dict = None

                    if coupon_dict is not None:
                        discounted_minor = compute_discounted_amount_minor(
                            amount_minor=amount_minor,
                            currency=currency,
                            coupon_dict=coupon_dict,
                        )
                        if discounted_minor is not None:
                            display_price_discounted = f'{format_money(amount_minor=discounted_minor, currency=currency)}{suffix}'

        enriched.append(
            item.model_dump(mode='python')
            | {
                'display_price': display_price,
                'display_price_discounted': display_price_discounted,
            }
        )

    return enriched
