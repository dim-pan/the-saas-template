from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.api.deps import get_supabase_client
from app.auth.deps import get_principal, get_current_user, Principal
from app.database.memberships import MembershipsHandler
from app.database.organizations import OrganizationsHandler
from app.database.types_autogen import PublicMemberships, PublicOrganizations, PublicUsers
from app.database.users import UsersHandler
from supabase import Client

ROLE_HIERARCHY: tuple[str, ...] = ('member', 'admin', 'owner')


def _role_level(role: str) -> int:
    if role in ROLE_HIERARCHY:
        return ROLE_HIERARCHY.index(role)
    return -1


@dataclass
class OrgRoleContext:
    """Result of require_org_role: org, principal, and (for users) membership and user."""

    org: PublicOrganizations
    principal: Principal
    membership: PublicMemberships | None  # None for service principal
    user: PublicUsers | None  # Set when principal.kind == 'user'


def require_org_membership(
    organization_id: UUID,
    db: Client = Depends(get_supabase_client),
    current_user: PublicUsers = Depends(get_current_user),
) -> PublicMemberships:
    membership = MembershipsHandler(db, organization_id=organization_id).get_for_user_in_org(
        current_user.id
    )
    return membership


def require_org_role(min_role: str):
    """Dependency factory: require principal to have at least min_role in this org. Returns OrgRoleContext."""

    min_level = _role_level(min_role)
    if min_level < 0:
        raise ValueError(f'require_org_role: unknown role {min_role!r}')

    def _dep(
        organization_id: UUID,
        principal: Principal = Depends(get_principal),
        db: Client = Depends(get_supabase_client),
    ) -> OrgRoleContext:
        org = OrganizationsHandler(db).get_item(organization_id)
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

        if principal.kind == 'service':
            return OrgRoleContext(org=org, principal=principal, membership=None, user=None)

        user = UsersHandler(db).get_item(UUID(principal.subject))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

        membership = MembershipsHandler(db, organization_id=organization_id).get_for_user_in_org(
            user.id
        )
        if _role_level(membership.role) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Insufficient permissions',
            )
        return OrgRoleContext(org=org, principal=principal, membership=membership, user=user)

    return _dep
