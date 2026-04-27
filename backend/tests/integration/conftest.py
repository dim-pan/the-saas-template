import os

import pytest
from dotenv import load_dotenv
from supabase import Client, create_client

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(dotenv_path=dotenv_path, override=False)

SUPABASE_TEST_URL = os.getenv('SUPABASE_TEST_URL')
SUPABASE_TEST_KEY = os.getenv('SUPABASE_TEST_KEY')


@pytest.fixture(scope='session')
def supabase_service_client() -> Client:
    """
    Real Supabase client for integration tests.

    Expected environment variables when running `supabase start` locally:
    - SUPABASE_TEST_URL
    - SUPABASE_TEST_KEY
    """

    url = SUPABASE_TEST_URL
    key = SUPABASE_TEST_KEY
    if not url or not key:
        pytest.fail(
            'Missing SUPABASE_TEST_URL and/or SUPABASE_TEST_KEY. '
            'Create a dedicated test Supabase instance and set these env vars before running integration tests.'
        )
    return create_client(url, key)
