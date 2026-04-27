/*
Add org-scoped billing primitives:

- organizations.billing_email
- organizations.stripe_customer_id (unique)
- subscriptions table (org hasMany subscriptions)

Free plan: no subscriptions row.
*/

alter table public.organizations
  add column if not exists billing_email text,
  add column if not exists stripe_customer_id text;

create unique index if not exists organizations_unique_stripe_customer_id
  on public.organizations (stripe_customer_id)
  where (stripe_customer_id is not null);

create index if not exists organizations_stripe_customer_id_idx
  on public.organizations (stripe_customer_id)
  where (stripe_customer_id is not null);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,
  archived boolean not null default false,

  organization_id uuid not null references public.organizations(id) on delete cascade,

  stripe_subscription_id text not null,
  stripe_subscription_item_id text,
  stripe_customer_id text,

  stripe_price_id text not null,
  stripe_product_id text not null,

  status text not null,
  cancel_at_period_end boolean not null default false,

  current_period_start timestamp with time zone,
  current_period_end timestamp with time zone,

  trial_end timestamp with time zone,
  cancel_request_at timestamp with time zone,
  ended_at timestamp with time zone
);

create index if not exists subscriptions_organization_id_idx
  on public.subscriptions (organization_id);

create unique index if not exists subscriptions_unique_stripe_subscription_id
  on public.subscriptions (stripe_subscription_id);

create index if not exists subscriptions_stripe_customer_id_idx
  on public.subscriptions (stripe_customer_id)
  where (stripe_customer_id is not null);

create index if not exists subscriptions_status_idx
  on public.subscriptions (status);
