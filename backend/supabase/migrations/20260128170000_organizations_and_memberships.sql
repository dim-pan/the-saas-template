-- Organizations (top-level tenant)
create table organizations (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,
  archived boolean not null default false,

  name text not null
);

-- Memberships (user <-> organization)
create table memberships (
  id uuid primary key default gen_random_uuid(),
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,
  archived boolean not null default false,

  organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid references users(id) on delete set null,

  role text not null default 'member',

  invited_by_id uuid references users(id) on delete set null,

  invited_email text,
  invitation_id text,
  invitation_expires_at timestamp with time zone,

  constraint membership_invite_fields_consistency check (
    -- Either this is a normal accepted membership (user_id is set),
    -- or it's an invite (user_id is null and invited_email+invitation_id are set).
    (user_id is not null)
    or
    (
      user_id is null
      and invited_email is not null
      and invitation_id is not null
    )
  )
);

-- Fast tenant-scoped lookups
create index memberships_organization_id_idx on memberships (organization_id);
create index memberships_user_id_idx on memberships (user_id);

-- A user should not have duplicate active memberships in the same org
create unique index memberships_unique_active_user_per_org
  on memberships (organization_id, user_id)
  where (archived = false and user_id is not null);

-- Invitation lookups
create unique index memberships_unique_invitation_id
  on memberships (invitation_id)
  where (invitation_id is not null);

create index memberships_invited_email_idx
  on memberships (invited_email)
  where (invited_email is not null);
