/*
Denormalized org billing read model.

Goal:
- Make "is this org paid and on which plan?" cheap to query everywhere.
- Keep `public.subscriptions` as the history/source-of-truth table.

These columns are written by Stripe webhooks and read by the frontend.
*/

alter table public.organizations
  add column if not exists billing_plan_key text,
  add column if not exists billing_status text,
  add column if not exists billing_is_paid boolean not null default false,
  add column if not exists billing_cancel_at_period_end boolean not null default false,
  add column if not exists billing_current_period_start timestamp with time zone,
  add column if not exists billing_current_period_end timestamp with time zone,
  add column if not exists billing_updated_at timestamp with time zone;

create index if not exists organizations_billing_is_paid_idx
  on public.organizations (billing_is_paid);

