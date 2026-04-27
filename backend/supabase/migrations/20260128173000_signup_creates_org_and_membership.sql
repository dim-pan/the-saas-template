-- Extend signup trigger to also create:
-- 1) a personal organization for the new user
-- 2) an owner membership linking the user to that organization
--
-- This is atomic (same transaction as auth.users insert) and avoids race conditions
-- between frontend/backends trying to "finish" signup.

create or replace function public.handle_new_user()
returns trigger
set search_path = ''
as $$
declare
  new_org_id uuid;
  display_name text;
begin
  -- Keep existing behavior: create the public.users row
  insert into public.users (id, full_name, avatar_url)
  values (new.id, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'avatar_url')
  on conflict (id) do update set
    full_name = excluded.full_name,
    avatar_url = excluded.avatar_url,
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
