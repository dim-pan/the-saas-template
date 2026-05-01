from types import SimpleNamespace
from uuid import uuid4

import app.api.routes.v1.memberships as memberships_routes
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from tests.unit.test_memberships_routes_last_owner import _membership_row
from tests.utils.db_query_test_stub import TestDbClient


def _admin_ctx() -> SimpleNamespace:
    """Fake OrgRoleContext for direct route calls when acting as admin."""
    return SimpleNamespace(
        membership=SimpleNamespace(role='admin'),
        org=None,
        principal=None,
        user=None,
    )


def test_admin_cannot_update_owner_membership_role() -> None:
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

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.update_membership_role(
            organization_id=organization_id,
            membership_id=owner_membership_id,
            payload=memberships_routes.UpdateMembershipRoleRequest(
                role=memberships_routes.MembershipRole.member
            ),
            db=db,  # type: ignore[arg-type]
            ctx=_admin_ctx(),
        )

    assert exc_info.value.status_code == 403


def test_admin_cannot_delete_owner_membership() -> None:
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

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.delete_membership(
            organization_id=organization_id,
            membership_id=owner_membership_id,
            db=db,  # type: ignore[arg-type]
            ctx=_admin_ctx(),
        )

    assert exc_info.value.status_code == 403


def test_admin_cannot_promote_to_owner() -> None:
    organization_id = uuid4()
    member_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=member_membership_id,
            organization_id=organization_id,
            role='member',
        )
    ]

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.update_membership_role(
            organization_id=organization_id,
            membership_id=member_membership_id,
            payload=memberships_routes.UpdateMembershipRoleRequest(role='owner'),
            db=db,  # type: ignore[arg-type]
            ctx=_admin_ctx(),
        )

    assert exc_info.value.status_code == 403


def test_admin_cannot_promote_member_to_admin() -> None:
    organization_id = uuid4()
    member_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=member_membership_id,
            organization_id=organization_id,
            role='member',
        )
    ]

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.update_membership_role(
            organization_id=organization_id,
            membership_id=member_membership_id,
            payload=memberships_routes.UpdateMembershipRoleRequest(role='admin'),
            db=db,  # type: ignore[arg-type]
            ctx=_admin_ctx(),
        )

    assert exc_info.value.status_code == 403


def test_admin_cannot_delete_admin_membership() -> None:
    organization_id = uuid4()
    admin_membership_id = uuid4()

    db = TestDbClient()
    db.storage['memberships'] = [
        _membership_row(
            membership_id=admin_membership_id,
            organization_id=organization_id,
            role='admin',
        )
    ]

    with pytest.raises(HTTPException) as exc_info:
        memberships_routes.delete_membership(
            organization_id=organization_id,
            membership_id=admin_membership_id,
            db=db,  # type: ignore[arg-type]
            ctx=_admin_ctx(),
        )

    assert exc_info.value.status_code == 403


def test_update_membership_role_request_normalizes_role_to_lowercase() -> None:
    payload = memberships_routes.UpdateMembershipRoleRequest(role='  OWNER  ')
    assert payload.role == memberships_routes.MembershipRole.owner


def test_update_membership_role_request_rejects_invalid_role() -> None:
    with pytest.raises(ValidationError):
        memberships_routes.UpdateMembershipRoleRequest(role='superadmin')
