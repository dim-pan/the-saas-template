import csv
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class CatalogCsvRow:
    key: str
    name: str | None
    description: str | None
    billing_type: str
    stripe_product_id: str
    stripe_price_id: str
    plan_family: str | None
    rank: int | None
    billing_interval: str | None
    billing_interval_count: int | None
    default_stripe_coupon_id: str | None
    override_stripe_coupon_id: str | None
    feature_set_json: str
    additional_data_json: str


def _require_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or value.strip() == '':
        raise ValueError(f'Invalid {field_name}')
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('Expected string or null')
    trimmed = value.strip()
    return trimmed if trimmed != '' else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError('Expected int or null')
    return value


def _require_int(value: object, *, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f'Expected int for {field_name}')
    return value


def _optional_list_of_str(value: object) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError('Expected list or null')
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError('Expected list of strings')
        items.append(item)
    return items


def _run_stripe_cli(args: list[str], *, env: dict[str, str]) -> dict:
    api_key = env.get('STRIPE_API_KEY')
    if api_key is None or api_key.strip() == '':
        raise RuntimeError('STRIPE_API_KEY is required to run Stripe CLI commands')

    result = subprocess.run(
        ['stripe', '--api-key', api_key, *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            'Stripe CLI command failed.\n'
            f'Command: stripe {" ".join(args)}\n'
            f'stdout: {result.stdout}\n'
            f'stderr: {result.stderr}\n'
        )
    raw_output = result.stdout.strip() if result.stdout.strip() != '' else result.stderr.strip()
    if raw_output == '':
        raise RuntimeError(
            'Stripe CLI returned no output.\n'
            f'Command: stripe {" ".join(args)}\n'
            f'stdout: {result.stdout}\n'
            f'stderr: {result.stderr}\n'
        )

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            'Stripe CLI output was not valid JSON.\n'
            f'Command: stripe {" ".join(args)}\n'
            f'output: {raw_output}\n'
        ) from exc
    if not isinstance(parsed, dict):
        raise RuntimeError('Stripe CLI output JSON was not an object')
    return parsed


def _build_stripe_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.get('STRIPE_API_KEY') is None or env.get('STRIPE_API_KEY', '').strip() == '':
        secret_key = env.get('STRIPE_SECRET_KEY')
        if secret_key is None or secret_key.strip() == '':
            raise RuntimeError(
                'Missing Stripe API key. Set STRIPE_API_KEY, or set STRIPE_SECRET_KEY and this script will use it.'
            )
        env['STRIPE_API_KEY'] = secret_key
    return env


def _ensure_stripe_cli_available(env: dict[str, str]) -> None:
    result = subprocess.run(
        ['stripe', '--version'],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            'Stripe CLI is not available. Install it and ensure `stripe` is on PATH.\n'
            f'stdout: {result.stdout}\n'
            f'stderr: {result.stderr}\n'
        )


def _create_product(
    *, name: str | None, description: str | None, key: str, env: dict[str, str]
) -> str:
    args: list[str] = ['products', 'create']
    if name is not None:
        args += ['-d', f'name={name}']
    if description is not None:
        args += ['-d', f'description={description}']
    args += ['-d', f'metadata[key]={key}']
    args += ['--confirm']
    created = _run_stripe_cli(args, env=env)
    product_id = created.get('id')
    return _require_str(product_id, field_name='product id')


def _create_price_one_off(
    *,
    product_id: str,
    currency: str,
    unit_amount: int,
    key: str,
    env: dict[str, str],
) -> str:
    args: list[str] = [
        'prices',
        'create',
        '-d',
        f'product={product_id}',
        '-d',
        f'currency={currency}',
        '-d',
        f'unit_amount={unit_amount}',
        '-d',
        f'metadata[key]={key}',
        '--confirm',
    ]
    created = _run_stripe_cli(args, env=env)
    price_id = created.get('id')
    return _require_str(price_id, field_name='price id')


def _create_price_recurring(
    *,
    product_id: str,
    currency: str,
    unit_amount: int,
    interval: str,
    interval_count: int,
    key: str,
    env: dict[str, str],
) -> str:
    args: list[str] = [
        'prices',
        'create',
        '-d',
        f'product={product_id}',
        '-d',
        f'currency={currency}',
        '-d',
        f'unit_amount={unit_amount}',
        '-d',
        f'recurring[interval]={interval}',
        '-d',
        f'recurring[interval_count]={interval_count}',
        '-d',
        f'metadata[key]={key}',
        '--confirm',
    ]
    created = _run_stripe_cli(args, env=env)
    price_id = created.get('id')
    return _require_str(price_id, field_name='price id')


def _project_root() -> Path:
    # backend/scripts/* -> repo root is two levels above backend/
    return Path(__file__).resolve().parents[2]


def _load_env() -> None:
    # Load backend/.env first (most relevant), then repo-root .env (if present).
    # Do not override already-set environment variables.
    scripts_dir = Path(__file__).resolve().parent
    backend_dir = scripts_dir.parent
    backend_env = backend_dir / '.env'
    load_dotenv(dotenv_path=backend_env, override=False)

    root_env = _project_root() / '.env'
    if root_env != backend_env:
        load_dotenv(dotenv_path=root_env, override=False)


def _write_csv(rows: list[CatalogCsvRow]) -> Path:
    root = _project_root()
    out_dir = root / '.temp' / 'stripe_seed'
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out_path = out_dir / f'stripe_catalog_seed_{timestamp}.csv'

    with out_path.open('w', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                'key',
                'name',
                'description',
                'billing_type',
                'stripe_product_id',
                'stripe_price_id',
                'plan_family',
                'rank',
                'billing_interval',
                'billing_interval_count',
                'default_stripe_coupon_id',
                'override_stripe_coupon_id',
                'feature_set',
                'additional_data',
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    'key': row.key,
                    'name': row.name or '',
                    'description': row.description or '',
                    'billing_type': row.billing_type,
                    'stripe_product_id': row.stripe_product_id,
                    'stripe_price_id': row.stripe_price_id,
                    'plan_family': row.plan_family or '',
                    'rank': '' if row.rank is None else str(row.rank),
                    'billing_interval': row.billing_interval or '',
                    'billing_interval_count': ''
                    if row.billing_interval_count is None
                    else str(row.billing_interval_count),
                    'default_stripe_coupon_id': row.default_stripe_coupon_id or '',
                    'override_stripe_coupon_id': row.override_stripe_coupon_id or '',
                    'feature_set': row.feature_set_json,
                    'additional_data': row.additional_data_json,
                }
            )

    return out_path


def main() -> None:
    _load_env()
    env = _build_stripe_env()
    _ensure_stripe_cli_available(env)

    scripts_dir = Path(__file__).resolve().parent
    spec_path = scripts_dir / 'dummy_stripe_products.json'
    raw = json.loads(spec_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError('Spec JSON must be an object')

    currency = _optional_str(raw.get('currency')) or 'usd'
    subscription_tiers_raw = raw.get('subscription_tiers')
    if subscription_tiers_raw is None:
        subscription_tiers: list[dict] = []
    else:
        if not isinstance(subscription_tiers_raw, list):
            raise ValueError('subscription_tiers must be a list')
        subscription_tiers = [item for item in subscription_tiers_raw if isinstance(item, dict)]

    one_off_items_raw = raw.get('one_off_items')
    if one_off_items_raw is None:
        one_off_items: list[dict] = []
    else:
        if not isinstance(one_off_items_raw, list):
            raise ValueError('one_off_items must be a list')
        one_off_items = [item for item in one_off_items_raw if isinstance(item, dict)]

    rows: list[CatalogCsvRow] = []

    for tier in subscription_tiers:
        key_prefix = _require_str(tier.get('key_prefix'), field_name='key_prefix')
        name = _optional_str(tier.get('name'))
        description = _optional_str(tier.get('description'))
        plan_family = _optional_str(tier.get('plan_family'))
        rank = _optional_int(tier.get('rank'))
        yearly_rank = _require_int(tier.get('yearly_rank'), field_name='yearly_rank')
        feature_set = _optional_list_of_str(tier.get('feature_set')) or []
        default_coupon_id = _optional_str(tier.get('default_stripe_coupon_id'))
        override_coupon_id = _optional_str(tier.get('override_stripe_coupon_id'))

        monthly_amount = tier.get('monthly_unit_amount')
        yearly_amount = tier.get('yearly_unit_amount')
        if not isinstance(monthly_amount, int) or monthly_amount <= 0:
            raise ValueError(f'{key_prefix}: monthly_unit_amount must be a positive integer')
        if not isinstance(yearly_amount, int) or yearly_amount <= 0:
            raise ValueError(f'{key_prefix}: yearly_unit_amount must be a positive integer')

        product_id = _create_product(name=name, description=description, key=key_prefix, env=env)

        monthly_key = f'{key_prefix}_monthly'
        monthly_price_id = _create_price_recurring(
            product_id=product_id,
            currency=currency,
            unit_amount=monthly_amount,
            interval='month',
            interval_count=1,
            key=monthly_key,
            env=env,
        )
        rows.append(
            CatalogCsvRow(
                key=monthly_key,
                name=name,
                description=description,
                billing_type='subscription',
                stripe_product_id=product_id,
                stripe_price_id=monthly_price_id,
                plan_family=plan_family,
                rank=rank,
                billing_interval='month',
                billing_interval_count=1,
                default_stripe_coupon_id=default_coupon_id,
                override_stripe_coupon_id=override_coupon_id,
                feature_set_json=json.dumps(feature_set),
                additional_data_json=json.dumps({}),
            )
        )

        yearly_key = f'{key_prefix}_yearly'
        yearly_price_id = _create_price_recurring(
            product_id=product_id,
            currency=currency,
            unit_amount=yearly_amount,
            interval='year',
            interval_count=1,
            key=yearly_key,
            env=env,
        )
        rows.append(
            CatalogCsvRow(
                key=yearly_key,
                name=name,
                description=description,
                billing_type='subscription',
                stripe_product_id=product_id,
                stripe_price_id=yearly_price_id,
                plan_family=plan_family,
                rank=yearly_rank,
                billing_interval='year',
                billing_interval_count=1,
                default_stripe_coupon_id=default_coupon_id,
                override_stripe_coupon_id=override_coupon_id,
                feature_set_json=json.dumps(feature_set),
                additional_data_json=json.dumps({}),
            )
        )

    for item in one_off_items:
        key = _require_str(item.get('key'), field_name='key')
        name = _optional_str(item.get('name'))
        description = _optional_str(item.get('description'))
        feature_set = _optional_list_of_str(item.get('feature_set')) or []
        default_coupon_id = _optional_str(item.get('default_stripe_coupon_id'))
        override_coupon_id = _optional_str(item.get('override_stripe_coupon_id'))
        unit_amount = item.get('unit_amount')
        if not isinstance(unit_amount, int) or unit_amount <= 0:
            raise ValueError(f'{key}: unit_amount must be a positive integer')

        product_id = _create_product(name=name, description=description, key=key, env=env)
        price_id = _create_price_one_off(
            product_id=product_id,
            currency=currency,
            unit_amount=unit_amount,
            key=key,
            env=env,
        )

        rows.append(
            CatalogCsvRow(
                key=key,
                name=name,
                description=description,
                billing_type='one_off',
                stripe_product_id=product_id,
                stripe_price_id=price_id,
                plan_family=None,
                rank=None,
                billing_interval=None,
                billing_interval_count=None,
                default_stripe_coupon_id=default_coupon_id,
                override_stripe_coupon_id=override_coupon_id,
                feature_set_json=json.dumps(feature_set),
                additional_data_json=json.dumps({}),
            )
        )

    out_path = _write_csv(rows)
    print(f'Wrote CSV: {out_path}')
    print(
        'Next: import rows into public.stripe_catalog_items (key/stripe_product_id/stripe_price_id/etc).'
    )


if __name__ == '__main__':
    main()
