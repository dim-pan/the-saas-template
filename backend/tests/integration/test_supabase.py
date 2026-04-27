from supabase import Client


def test_supabase_smoke_select_users(supabase_service_client: Client) -> None:
    # Read-only check that local Supabase is reachable and PostgREST works.
    result = supabase_service_client.table('users').select('id').range(0, 0).execute()
    data = result.data
    assert data is None or isinstance(data, list)
