/*
Prevent an organization from ever ending up with zero active owners.

Why:
- API-level checks are necessary, but concurrent operations can still race.
- This trigger provides defense-in-depth at the database layer.
*/

create or replace function public.prevent_last_owner_removal()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  other_owner_exists boolean;
begin
  -- Only enforce for rows that are currently active owners and are being removed/demoted.
  if (tg_op = 'UPDATE') then
    if (old.archived = false and old.role = 'owner') then
      if (
        (new.archived = true) -- archiving the membership
        or (new.role is distinct from 'owner') -- demoting from owner
      ) then
        select exists(
          select 1
          from public.memberships m
          where
            m.organization_id = old.organization_id
            and m.archived = false
            and m.role = 'owner'
            and m.id <> old.id
          limit 1
        ) into other_owner_exists;

        if (other_owner_exists is not true) then
          raise exception 'Organization must have at least one owner';
        end if;
      end if;
    end if;

    return new;
  end if;

  if (tg_op = 'DELETE') then
    if (old.archived = false and old.role = 'owner') then
      select exists(
        select 1
        from public.memberships m
        where
          m.organization_id = old.organization_id
          and m.archived = false
          and m.role = 'owner'
          and m.id <> old.id
        limit 1
      ) into other_owner_exists;

      if (other_owner_exists is not true) then
        raise exception 'Organization must have at least one owner';
      end if;
    end if;

    return old;
  end if;

  return coalesce(new, old);
end;
$$;

drop trigger if exists memberships_prevent_last_owner_removal on public.memberships;
create trigger memberships_prevent_last_owner_removal
before update or delete on public.memberships
for each row
execute function public.prevent_last_owner_removal();
