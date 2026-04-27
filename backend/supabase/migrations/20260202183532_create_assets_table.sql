create table if not exists assets (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null unique,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone,
  deleted_at timestamp with time zone default null,

  user_id uuid references users(id) on delete set null,
  organization_id uuid not null references organizations(id) on delete cascade,
  
  filename text not null,

  storage_key text not null unique,
  thumbnail_url text default null,
  mime_type text not null,
  status text not null default 'pending'
    check (status in ('pending', 'uploaded', 'failed')),
  size_bytes bigint,
  provider text not null -- r2, image, stream
);

create index if not exists assets_user_id_idx on assets (user_id);
create index if not exists assets_organization_id_idx on assets (organization_id);
