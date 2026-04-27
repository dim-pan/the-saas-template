/*
Jobs / worker tasks table.

Tracks task status and payload (data) per organization.
*/

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  external_id text,

  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,

  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete restrict,

  status text not null default 'queued'
    check (status in ('queued', 'processing', 'completed', 'failed')),
  task text not null,

  submitted_at timestamp with time zone not null default now(),
  finished_at timestamp with time zone,

  data jsonb not null default '{}'::jsonb
);

create index if not exists jobs_organization_id_idx
  on public.jobs (organization_id);

create index if not exists jobs_user_id_idx
  on public.jobs (user_id);

create index if not exists jobs_status_idx
  on public.jobs (status);
