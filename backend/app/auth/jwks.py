import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import SUPABASE_JWKS_URL, SUPABASE_URL

JWKS_TTL_SECONDS = 10 * 60

_jwks_cached_at: float | None = None
_jwks_cache: dict[str, Any] | None = None


def _supabase_url() -> str:
    url = SUPABASE_URL
    if not url:
        raise RuntimeError('SUPABASE_URL must be set')
    return url.rstrip('/')


def jwks_url() -> str:
    explicit = SUPABASE_JWKS_URL
    if explicit:
        return explicit
    return f'{_supabase_url()}/auth/v1/.well-known/jwks.json'


def _fetch_jwks() -> dict[str, Any]:
    response = httpx.get(jwks_url(), timeout=10.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or 'keys' not in payload:
        raise RuntimeError('Invalid JWKS response')
    return payload


def get_jwks(force_refresh: bool = False) -> dict[str, Any]:
    global _jwks_cache, _jwks_cached_at

    now = time.time()
    is_stale = _jwks_cached_at is None or (now - _jwks_cached_at) > JWKS_TTL_SECONDS
    if force_refresh or _jwks_cache is None or is_stale:
        _jwks_cache = _fetch_jwks()
        _jwks_cached_at = now
    return _jwks_cache


def _allowed_issuers() -> set[str]:
    base = _supabase_url()
    return {base, f'{base}/auth/v1'}


def _allowed_jwt_algorithms() -> list[str]:
    """
    Server-side allowlist of acceptable JWT signing algorithms.
    Supabase uses RS256 (hosted) or ES256 (e.g. local Auth).

    """
    return ['RS256', 'ES256']


def verify_supabase_jwt_with_jwks(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token'
        ) from exc

    kid = header.get('kid')
    header_alg = header.get('alg')
    if not isinstance(kid, str) or not isinstance(header_alg, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token header',
        )

    allowed_algorithms = _allowed_jwt_algorithms()
    if header_alg not in allowed_algorithms:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token algorithm',
        )

    def decode_with(jwks: dict[str, Any]) -> dict[str, Any] | None:
        keys = jwks.get('keys')
        if not isinstance(keys, list):
            return None
        matching = next(
            (key for key in keys if isinstance(key, dict) and key.get('kid') == kid),
            None,
        )
        if not isinstance(matching, dict):
            return None

        key_type = matching.get('kty')
        if key_type not in ('RSA', 'EC'):
            return None

        key_alg = matching.get('alg')
        if isinstance(key_alg, str) and key_alg not in allowed_algorithms:
            return None
        try:
            claims = jwt.decode(
                token,
                matching,
                algorithms=allowed_algorithms,
                audience='authenticated',
                options={'verify_iss': False},
            )
        except JWTError:
            return None

        iss = claims.get('iss')
        if isinstance(iss, str) and iss in _allowed_issuers():
            return claims
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token issuer',
        )

    claims = decode_with(get_jwks(force_refresh=False))
    if claims is not None:
        return claims

    claims = decode_with(get_jwks(force_refresh=True))
    if claims is not None:
        return claims

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
