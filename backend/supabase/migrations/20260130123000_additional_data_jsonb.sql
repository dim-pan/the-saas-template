/*
Add a flexible metadata column to core app tables.

Decision:
- additional_data is NOT NULL with a default empty object to avoid NULL handling in code.

Scope (Option A):
- public.users
- public.organizations
- public.memberships
- public.subscriptions
*/

alter table public.users
  add column if not exists additional_data jsonb not null default '{}'::jsonb;

alter table public.organizations
  add column if not exists additional_data jsonb not null default '{}'::jsonb;

alter table public.memberships
  add column if not exists additional_data jsonb not null default '{}'::jsonb;

alter table public.subscriptions
  add column if not exists additional_data jsonb not null default '{}'::jsonb;
