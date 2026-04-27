from functools import lru_cache

from supabase import Client, create_client

from app.config import SUPABASE_KEY, SUPABASE_URL


@lru_cache(maxsize=1)
def get_database() -> Client:
    url = SUPABASE_URL
    key = SUPABASE_KEY
    if not url or not key:
        raise ValueError('SUPABASE_URL and SUPABASE_KEY must be set')

    return create_client(url, key)
