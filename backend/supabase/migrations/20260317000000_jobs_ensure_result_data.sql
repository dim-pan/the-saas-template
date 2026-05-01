-- Ensure result_data exists on jobs (e.g. if table was created before it was in schema).
alter table public.jobs
  add column if not exists result_data jsonb not null default '{}'::jsonb;
