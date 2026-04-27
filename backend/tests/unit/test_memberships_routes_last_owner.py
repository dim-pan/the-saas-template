from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import app.api.routes.v1.memberships as memberships_routes
import pytest
from fastapi import HTTPException
from tests.utils.db_query_test_stub import TestDbClient


def _membership_row(
    *,
    membership_id: UUID,
    organization_id: UUID,
    role: str,
    is_archived: bool = False,
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    return {
        'additional_data': {},
        'id': str(membership_id),
        'organization_id': str(organization_id),
        'role': role,
        'archived': is_archived,
        'created_at': now.isoformat(),
        'updated_at': None,
        'user_id': None,
        'invited_by_id': None,
        'invited_email': None,
        'invitation_id': None,
        'invitation_expires_at': None,
    }


def _owner_ctx() -> SimpleNamespace:
    """Fake OrgRoleContext for direct route calls when acting as owner."""
    return SimpleNamespace(
        membership=SimpleNamespace(role='owner'),
        org=None,
        principal=None,
        user=None,
    )


def test_update_membership_role_rejects_demoting_last_owner() -> None:
    organization_id = uuid4()
    owner_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=owner_membership_id,
            organization_id=organization_id,
            role='owner',
        ),
        _membership_row(
            membership_id=uuid4(),
            organization_id=organization_id,
            role='member',
        ),
    ]

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.update_membership_role(
            organization_id=organization_id,
            membership_id=owner_membership_id,
            payload=memberships_routes.UpdateMembershipRoleRequest(
                role=memberships_routes.MembershipRole.member
            ),
            db=db,  # type: ignore[arg-type]
            ctx=_owner_ctx(),  # type: ignore[arg-type] # noqa: PGH003
        )

    assert exc_info.value.status_code == 409


def test_update_membership_role_allows_demoting_owner_when_another_owner_exists() -> None:
    organization_id = uuid4()
    owner_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=owner_membership_id,
            organization_id=organization_id,
            role='owner',
        ),
        _membership_row(
            membership_id=uuid4(),
            organization_id=organization_id,
            role='owner',
        ),
    ]

    updated = memberships_routes.update_membership_role(
        organization_id=organization_id,
        membership_id=owner_membership_id,
        payload=memberships_routes.UpdateMembershipRoleRequest(
            role=memberships_routes.MembershipRole.member
        ),
        db=db,  # type: ignore[arg-type]
        ctx=_owner_ctx(),  # type: ignore[arg-type] # noqa: PGH003
    )

    assert str(updated.id) == str(owner_membership_id)
    assert updated.role == 'member'


def test_delete_membership_rejects_deleting_last_owner() -> None:
    organization_id = uuid4()
    owner_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=owner_membership_id,
            organization_id=organization_id,
            role='owner',
        ),
    ]

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.delete_membership(
            organization_id=organization_id,
            membership_id=owner_membership_id,
            db=db,  # type: ignore[arg-type]
            ctx=_owner_ctx(),  # type: ignore[arg-type] # noqa: PGH003
        )

    assert exc_info.value.status_code == 409


def test_delete_membership_allows_deleting_owner_when_another_owner_exists() -> None:
    organization_id = uuid4()
    owner_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=owner_membership_id,
            organization_id=organization_id,
            role='owner',
        ),
        _membership_row(
            membership_id=uuid4(),
            organization_id=organization_id,
            role='owner',
        ),
    ]

    deleted = memberships_routes.delete_membership(
        organization_id=organization_id,
        membership_id=owner_membership_id,
        db=db,  # type: ignore[arg-type]
        ctx=_owner_ctx(),  # type: ignore[arg-type] # noqa: PGH003
    )

    assert str(deleted.id) == str(owner_membership_id)
    assert deleted.archived is True
