/*
Stripe webhook event ingestion table.

Goals:
- Idempotency (unique stripe_event_id)
- Debuggability (payload + error fields)
- Safe environment separation (livemode)
*/

create table if not exists public.stripe_webhook_events (
  id uuid primary key default gen_random_uuid(),

  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,

  organization_id uuid references public.organizations(id) on delete set null,
  stripe_customer_id text,

  stripe_event_id text not null,
  type text not null,
  livemode boolean not null,

  received_at timestamp with time zone not null default now(),
  processed_at timestamp with time zone,

  processing_error text,

  payload jsonb not null default '{}'::jsonb,
  additional_data jsonb not null default '{}'::jsonb
);

create unique index if not exists stripe_webhook_events_unique_stripe_event_id
  on public.stripe_webhook_events (stripe_event_id);

create index if not exists stripe_webhook_events_organization_id_idx
  on public.stripe_webhook_events (organization_id)
  where (organization_id is not null);

create index if not exists stripe_webhook_events_stripe_customer_id_idx
  on public.stripe_webhook_events (stripe_customer_id)
  where (stripe_customer_id is not null);

create index if not exists stripe_webhook_events_type_idx
  on public.stripe_webhook_events (type);

create index if not exists stripe_webhook_events_received_at_idx
  on public.stripe_webhook_events (received_at);
