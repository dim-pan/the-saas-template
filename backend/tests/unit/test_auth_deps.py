import pytest
from fastapi import HTTPException

from app.auth import deps as auth_deps


@pytest.mark.anyio
async def test_get_principal_raises_401_when_no_credentials() -> None:
    """Without X-API-Key or Bearer token, get_principal raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        await auth_deps.get_principal(x_api_key=None, creds=None)
    assert exc_info.value.status_code == 401
    assert 'credentials' in (exc_info.value.detail or '').lower()
