from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_supabase_client
from app.auth.jwks import verify_supabase_jwt_with_jwks
from app.config import BACKEND_SECRET, DEV_AUTH_BYPASS_ENABLED, DEV_DEFAULT_USER_ID, ENV
from app.database.types_autogen import PublicUsers
from app.database.users import UsersHandler
from app.utils.logger import get_logger
from supabase import Client

logger = get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """Unified identity from either master API key (service) or JWT (user)."""

    kind: Literal['service', 'user']
    subject: str  # "service:master" or user_id (uuid string)
    roles: frozenset[str]


def _verify_master_key(x_api_key: str | None) -> Principal | None:
    if not x_api_key:
        return None
    if not BACKEND_SECRET or x_api_key != BACKEND_SECRET:
        logger.warning(
            'get_principal: X-API-Key present but invalid (key mismatch or BACKEND_SECRET unset)'
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid API key',
        )
    return Principal(kind='service', subject='service:master', roles=frozenset({'owner'}))


def _verify_token_via_supabase(db: Client, token: str) -> UUID:
    try:
        response = db.auth.get_user(jwt=token)
    except Exception as exc:
        # Map auth failures to 401; don't crash on invalid/expired JWT.
        status_code_value = getattr(exc, 'status_code', None)
        if status_code_value == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
            ) from exc
        raise

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
        )
    user_id = response.user.id
    try:
        return UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token'
        ) from exc


def _verify_jwt_for_principal(
    creds: HTTPAuthorizationCredentials | None, db: Client
) -> Principal | None:
    if not creds or creds.scheme.lower() != 'bearer':
        return None
    token = creds.credentials
    if ENV == 'dev':
        user_id = _verify_token_via_supabase(db, token)
    else:
        user_id = _verify_token_via_jwks(token)
    # Role is org-relative; resolved per-org in require_org_role.
    return Principal(kind='user', subject=str(user_id), roles=frozenset())


def _parse_dev_user_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid dev user id'
        ) from exc


async def get_principal(
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Client = Depends(get_supabase_client),
    dev_user_id: str | None = Header(default=None, alias='X-Dev-User-Id'),
) -> Principal:
    """Resolve principal from X-API-Key (service) or Bearer JWT (user). Prefer API key if both present."""
    principal = _verify_master_key(x_api_key)
    if principal is not None:
        return principal

    if ENV == 'dev' and DEV_AUTH_BYPASS_ENABLED:
        resolved_dev_user_id = dev_user_id or DEV_DEFAULT_USER_ID
        if resolved_dev_user_id is not None:
            user_id = _parse_dev_user_id(resolved_dev_user_id)
            logger.info(
                'get_principal: dev bypass user resolved user_id=%s (X-Dev-User-Id=%s DEV_DEFAULT_USER_ID=%s)',
                user_id,
                dev_user_id,
                DEV_DEFAULT_USER_ID,
            )
            return Principal(kind='user', subject=str(user_id), roles=frozenset())

    principal = _verify_jwt_for_principal(creds, db)
    if principal is not None:
        return principal

    logger.warning(
        'get_principal: no valid credentials (no/invalid Bearer, no valid X-API-Key), returning 401'
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Missing credentials',
    )


# Role hierarchy: lowest to highest. A principal with a higher role can do anything a lower role can.
ROLE_HIERARCHY: tuple[str, ...] = ('member', 'admin', 'owner')


def _role_level(role: str) -> int:
    """Return the level of a role (0 = lowest). Unknown roles return -1."""
    if role in ROLE_HIERARCHY:
        return ROLE_HIERARCHY.index(role)
    return -1


def require_role(min_role: str):
    """
    Dependency factory: require principal to have at least the given role level.
    Permissions cascade: e.g. require_role('member') allows member, admin, and owner.
    So you only specify the minimum required role; higher roles are included automatically.
    """

    min_level = _role_level(min_role)
    if min_level < 0:
        raise ValueError(f'require_role: unknown role {min_role!r}. Known roles: {ROLE_HIERARCHY}')

    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        # User principals have no global role; allow for routes without org context.
        if principal.kind == 'user':
            return principal
        principal_level = max((_role_level(r) for r in principal.roles), default=-1)
        if principal_level >= min_level:
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Forbidden',
        )

    return _dep


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing bearer token',
        )
    if credentials.scheme.lower() != 'bearer':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid authentication scheme',
        )
    return credentials.credentials


def _verify_token_via_jwks(token: str) -> UUID:
    claims = verify_supabase_jwt_with_jwks(token)
    sub = claims.get('sub')
    try:
        return UUID(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token'
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Client = Depends(get_supabase_client),
    dev_user_id: str | None = Header(default=None, alias='X-Dev-User-Id'),
) -> PublicUsers:
    if ENV == 'dev' and DEV_AUTH_BYPASS_ENABLED:
        resolved_dev_user_id = dev_user_id or DEV_DEFAULT_USER_ID
        if resolved_dev_user_id is not None:
            user_id = _parse_dev_user_id(resolved_dev_user_id)
            user = UsersHandler(db).get_item(user_id, require_org=True)
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
            logger.info(
                'get_current_user: dev bypass user resolved user_id=%s (X-Dev-User-Id=%s DEV_DEFAULT_USER_ID=%s)',
                user_id,
                dev_user_id,
                DEV_DEFAULT_USER_ID,
            )
            return user

    token = get_bearer_token(credentials)
    if ENV == 'dev':
        user_id = _verify_token_via_supabase(db, token)
    else:
        user_id = _verify_token_via_jwks(token)
    user = UsersHandler(db).get_item(user_id, require_org=True)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
    return user
