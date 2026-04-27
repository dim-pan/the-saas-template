from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, RootModel, field_validator
from supabase import Client

from app.api.deps import get_supabase_client
from app.api.org_deps import OrgRoleContext, require_org_role
from app.database.memberships import MembershipsHandler
from app.database.types_autogen import PublicMemberships


class MembershipRole(StrEnum):
    owner = 'owner'
    admin = 'admin'
    member = 'member'


# API contract models (request/response) - keep these at the top for readability.
class MembershipResult(PublicMemberships):
    pass


class MembershipListResult(RootModel[list[MembershipResult]]):
    pass


class UpdateMembershipRoleRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: MembershipRole

    @field_validator('role', mode='before')
    @classmethod
    def _normalize_role(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


router = APIRouter(prefix='/org/{organization_id}', tags=['memberships'])


@router.get('/memberships', response_model=MembershipListResult)
def list_org_memberships(
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('member')),
) -> MembershipListResult:
    memberships = MembershipsHandler(db, organization_id=organization_id)
    rows = memberships.list_items()
    return MembershipListResult.model_validate(
        [MembershipResult.model_validate(row, from_attributes=True) for row in rows]
    )


@router.get('/membership', response_model=MembershipResult)
def get_my_membership(
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('member')),
) -> MembershipResult:
    if ctx.membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')
    membership_row = ctx.membership
    return MembershipResult.model_validate(membership_row, from_attributes=True)


@router.patch('/memberships/{membership_id}', response_model=MembershipResult)
def update_membership_role(
    organization_id: UUID,
    membership_id: UUID,
    payload: UpdateMembershipRoleRequest,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('admin')),
) -> MembershipResult:
    actor_membership = ctx.membership
    if actor_membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')

    memberships = MembershipsHandler(db, organization_id=organization_id)
    existing_membership = memberships.get_item(membership_id)
    if existing_membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    if actor_membership.role == 'admin':
        if existing_membership.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions',
            )
        if payload.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions',
            )

    is_demoting_owner = existing_membership.role == 'owner' and payload.role != 'owner'
    if is_demoting_owner and not memberships.has_another_active_owner(
        excluding_membership_id=membership_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Organization must have at least one owner',
        )

    updated = memberships.update_item(membership_id, {'role': str(payload.role)})
    return MembershipResult.model_validate(updated, from_attributes=True)


@router.delete('/memberships/{membership_id}', response_model=MembershipResult)
def delete_membership(
    organization_id: UUID,
    membership_id: UUID,
    db: Client = Depends(get_supabase_client),
    ctx: OrgRoleContext = Depends(require_org_role('admin')),
) -> MembershipResult:
    actor_membership = ctx.membership
    if actor_membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User token required')

    memberships = MembershipsHandler(db, organization_id=organization_id)
    existing_membership = memberships.get_item(membership_id)
    if existing_membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    if actor_membership.role == 'admin' and existing_membership.role == 'owner':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Insufficient permissions',
        )

    is_deleting_owner = existing_membership.role == 'owner'
    if is_deleting_owner and not memberships.has_another_active_owner(
        excluding_membership_id=membership_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Organization must have at least one owner',
        )

    deleted = memberships.delete_item(membership_id)
    return MembershipResult.model_validate(deleted, from_attributes=True)
