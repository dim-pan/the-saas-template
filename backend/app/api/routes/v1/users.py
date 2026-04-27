from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import AnyUrl, BaseModel, ConfigDict
from supabase import Client

from app.api.deps import get_supabase_client
from app.api.org_deps import OrgRoleContext, require_org_role
from app.database.types_autogen import PublicUsers
from app.database.users import UsersHandler


# API contract models (request/response) - keep these at the top for readability.
class UserResult(PublicUsers):
    pass


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str | None = None
    full_name: str | None = None
    avatar_url: AnyUrl | None = None


router = APIRouter(prefix='/org/{organization_id}/users', tags=['users'])


@router.get('/{user_id}', response_model=UserResult)
def get_user(
    organization_id: UUID,
    user_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('member')),
) -> UserResult:
    user = UsersHandler(db).get_item(user_id)
    return UserResult.model_validate(user, from_attributes=True)


@router.patch('/{user_id}', response_model=UserResult)
def update_user(
    organization_id: UUID,
    user_id: UUID,
    payload: UpdateUserRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('member')),
) -> UserResult:
    updated = UsersHandler(db).update_item(
        user_id, payload.model_dump(exclude_unset=True, mode='json')
    )
    return UserResult.model_validate(updated, from_attributes=True)


@router.delete('/{user_id}', response_model=UserResult)
def delete_user(
    organization_id: UUID,
    user_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('member')),
) -> UserResult:
    updated = UsersHandler(db).delete_item(user_id)
    return UserResult.model_validate(updated, from_attributes=True)
