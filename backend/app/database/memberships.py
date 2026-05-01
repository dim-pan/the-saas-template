from enum import StrEnum
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.database.handler import DatabaseHandler, Filter
from app.database.types_autogen import (
    PublicMemberships,
    PublicMembershipsInsert,
    PublicMembershipsUpdate,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MembershipRole(StrEnum):
    owner = 'owner'
    admin = 'admin'
    member = 'member'


class MembershipsHandler(
    DatabaseHandler[PublicMemberships, PublicMembershipsInsert, PublicMembershipsUpdate]
):
    organization_id: UUID

    def __init__(self, client: Client, *, organization_id: UUID) -> None:
        super().__init__(
            client,
            table='memberships',
            row_model=PublicMemberships,
            organization_id=organization_id,
        )

    def list_for_user(self, user_id: UUID) -> list[PublicMemberships]:
        return self.list_items(filters=[Filter(column='user_id', op='eq', value=user_id)])

    def get_for_user_in_org(self, user_id: UUID) -> PublicMemberships:
        rows = self.list_items(filters=[Filter(column='user_id', op='eq', value=user_id)])
        if len(rows) == 0:
            logger.warning(
                'get_for_user_in_org: no membership org=%s user=%s -> raising 403',
                self.organization_id,
                user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Not a member of this organization',
            )
        return rows[0]

    def list_active_owners(self) -> list[PublicMemberships]:
        return self.list_items(
            filters=[Filter(column='role', op='eq', value=MembershipRole.owner.value)]
        )

    def has_another_active_owner(self, *, excluding_membership_id: UUID) -> bool:
        owners = self.list_active_owners()
        for owner_membership in owners:
            if owner_membership.id != excluding_membership_id:
                return True
        return False
