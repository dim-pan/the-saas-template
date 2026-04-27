/*
Denormalize email onto public.users and remove unused website field.

Changes:
- public.users.email (NOT NULL, UNIQUE)
- backfill email from auth.users
- drop public.users.website
- update public.handle_new_user() trigger function to populate email on signup
*/

alter table public.users
  add column if not exists email text;

update public.users u
set email = au.email
from auth.users au
where au.id = u.id
  and u.email is null;

do $$
begin
  if exists (
    select 1
    from public.users u
    where u.email is null or u.email = ''
    limit 1
  ) then
    raise exception 'public.users.email cannot be null/empty; ensure all auth.users have an email before applying NOT NULL';
  end if;
end;
$$;

alter table public.users
  alter column email set not null;

create unique index if not exists users_unique_email_idx
  on public.users (email);

alter table public.users
  drop column if exists website;

create or replace function public.handle_new_user()
returns trigger
set search_path = ''
as $$
declare
  new_org_id uuid;
  display_name text;
begin
  -- Keep existing behavior: create the public.users row
  insert into public.users (id, full_name, avatar_url, email)
  values (
    new.id,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'avatar_url',
    new.email
  )
  on conflict (id) do update set
    full_name = excluded.full_name,
    avatar_url = excluded.avatar_url,
    email = excluded.email,
    updated_at = now();

  -- Create the user's personal org + membership
  display_name := coalesce(
    nullif(new.raw_user_meta_data->>'full_name', ''),
    nullif(split_part(new.email, '@', 1), ''),
    'Personal'
  );

  insert into public.organizations (name)
  values (display_name || '''s Organization')
  returning id into new_org_id;

  insert into public.memberships (
    organization_id,
    user_id,
    role
  )
  values (
    new_org_id,
    new.id,
    'owner'
  );

  return new;
end;
$$ language plpgsql security definer;
