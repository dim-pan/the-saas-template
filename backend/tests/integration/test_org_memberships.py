from uuid import UUID, uuid4

from app.database.handler import Filter
from app.database.memberships import MembershipsHandler
from app.database.organizations import OrganizationsHandler
from app.database.types_autogen import (
    PublicMembershipsInsert,
    PublicOrganizationsInsert,
)
from supabase import Client


def test_org_and_membership_crud_happy_path(
    supabase_service_client: Client,
) -> None:
    # Note: We create an invite-style membership (user_id is null) to avoid relying on auth users.
    org_id: str | None = None
    membership_id: str | None = None

    try:
        created_org = OrganizationsHandler(supabase_service_client).create_item(
            PublicOrganizationsInsert(name=f'test-org-{uuid4()}')
        )
        org_id = str(created_org.id)

        memberships = MembershipsHandler(supabase_service_client, organization_id=UUID(org_id))

        invitation_id = f'inv_{uuid4().hex}'
        created_membership = memberships.create_item(
            PublicMembershipsInsert(
                organization_id=UUID(org_id),
                role='member',
                invited_email='invited@example.com',
                invitation_id=invitation_id,
            )
        )
        membership_id = str(created_membership.id)

        fetched = memberships.get_item(UUID(membership_id))
        assert str(fetched.id) == membership_id
        assert str(fetched.organization_id) == org_id

        updated = memberships.update_item(
            UUID(membership_id),
            {'role': 'admin'},
        )
        assert updated.role == 'admin'

        rows = memberships.list_items(
            filters=[Filter(column='id', op='in', value=[UUID(membership_id)])]
        )
        assert len(rows) == 1
        assert str(rows[0].id) == membership_id

        deleted = memberships.delete_item(UUID(membership_id))
        assert deleted.archived is True
    finally:
        # Hard cleanup so local dev DB doesn't accumulate junk.
        if membership_id is not None:
            supabase_service_client.table('memberships').delete().eq('id', membership_id).execute()
        if org_id is not None:
            supabase_service_client.table('organizations').delete().eq('id', org_id).execute()
