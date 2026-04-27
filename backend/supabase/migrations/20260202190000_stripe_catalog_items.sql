/*
Stripe catalog items.

Goals:
- Store Stripe Product/Price IDs in the DB (per-environment DB separation)
- Support both subscriptions and one-off purchases in one table
- Provide a stable internal `key` used by the app code
- Support coupon defaults + per-item coupon overrides
- Support a feature list for pricing cards
*/

create table if not exists public.stripe_catalog_items (
  id uuid primary key default gen_random_uuid(),

  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,
  archived boolean not null default false,

  -- Stable internal identifier used by code (same across environments)
  key text not null,

  -- Optional display fields
  name text,
  description text,

  -- For pricing cards bullet points (avoid NULL handling in code)
  feature_set text[] not null default '{}'::text[],

  -- 'subscription' or 'one_off'
  billing_type text not null,

  -- Stripe mapping for THIS env/DB
  stripe_product_id text not null,
  stripe_price_id text not null,

  -- Upgrade/downgrade detection (subscriptions only)
  plan_family text,
  rank integer,

  -- Optional subscription cadence snapshot (subscriptions only)
  billing_interval text,
  billing_interval_count integer,

  -- Coupons (global per catalog item)
  default_stripe_coupon_id text,
  override_stripe_coupon_id text,

  additional_data jsonb not null default '{}'::jsonb,

  constraint stripe_catalog_items_unique_key unique (key),
  constraint stripe_catalog_items_unique_stripe_price_id unique (stripe_price_id),

  constraint stripe_catalog_items_billing_type_check check (
    billing_type in ('subscription', 'one_off')
  ),

  constraint stripe_catalog_items_subscription_fields_check check (
    (
      billing_type = 'one_off'
      and plan_family is null
      and rank is null
      and billing_interval is null
      and billing_interval_count is null
    )
    or
    (
      billing_type = 'subscription'
      and plan_family is not null
      and rank is not null
    )
  )
);

create index if not exists stripe_catalog_items_billing_type_idx
  on public.stripe_catalog_items (billing_type);

create index if not exists stripe_catalog_items_plan_family_rank_idx
  on public.stripe_catalog_items (plan_family, rank)
  where (billing_type = 'subscription' and archived = false);
