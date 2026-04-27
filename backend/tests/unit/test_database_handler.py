from uuid import UUID, uuid4

import pytest
from app.database.handler import DatabaseHandler, Filter
from fastapi import HTTPException
from pydantic import BaseModel
from tests.utils.db_query_test_stub import TestDbClient


class ProjectRow(BaseModel):
    id: str
    organization_id: str | None = None
    archived: bool = False


class UserRow(BaseModel):
    id: str = 'unused'
    archived: bool = False


def test_org_scoped_requires_organization_id() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='projects', row_model=ProjectRow)
    with pytest.raises(ValueError, match='organization_id is required'):
        crud.list_items()
    with pytest.raises(ValueError, match='organization_id is required'):
        crud.create_item({'id': str(uuid4())})


def test_global_table_does_not_require_organization_id() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)
    assert crud.list_items() == []


def test_list_items_excludes_archived_by_default() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)

    active_id = str(uuid4())
    archived_id = str(uuid4())
    crud.create_item({'id': active_id, 'archived': False})
    crud.create_item({'id': archived_id, 'archived': True})

    rows = crud.list_items()
    assert [row.id for row in rows] == [active_id]


def test_get_item_excludes_archived_by_default() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)

    archived_id = uuid4()
    crud.create_item({'id': str(archived_id), 'archived': True})

    with pytest.raises(HTTPException) as exc_info:
        crud.get_item(archived_id)
    assert exc_info.value.status_code == 404


def test_update_item_refuses_to_update_archived_rows() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)

    entity_id = uuid4()
    crud.create_item({'id': str(entity_id), 'archived': True})

    with pytest.raises(HTTPException) as exc_info:
        crud.update_item(entity_id, {'archived': False})
    assert exc_info.value.status_code == 404


def test_restore_item_unarchives_row() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)

    entity_id = uuid4()
    crud.create_item({'id': str(entity_id), 'archived': True})

    restored = crud.restore_item(entity_id)
    assert restored.archived is False

    fetched = crud.get_item(entity_id)
    assert fetched.id == str(entity_id)


def test_list_items_rejects_non_positive_limit() -> None:
    db = TestDbClient()
    crud = DatabaseHandler(db, table='users', row_model=UserRow)

    with pytest.raises(HTTPException) as exc_info:
        crud.list_items(limit=0)
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        crud.list_items(limit=-1)
    assert exc_info.value.status_code == 400


def test_create_requires_and_validates_organization_id() -> None:
    db = TestDbClient()
    org_id = uuid4()
    crud = DatabaseHandler(db, table='projects', row_model=ProjectRow, organization_id=org_id)

    entity_id = uuid4()
    with pytest.raises(ValueError, match='payload organization_id is required'):
        crud.create_item({'id': str(entity_id), 'archived': False})

    with pytest.raises(ValueError, match='payload organization_id does not match'):
        crud.create_item({'id': str(uuid4()), 'organization_id': str(uuid4())})

    created = crud.create_item(
        {'id': str(uuid4()), 'archived': False, 'organization_id': str(org_id)}
    )
    assert created.organization_id == str(org_id)


def test_list_items_in_filter_is_org_scoped() -> None:
    db = TestDbClient()
    org_a = uuid4()
    org_b = uuid4()

    id1 = uuid4()
    id2 = uuid4()
    id3 = uuid4()

    DatabaseHandler(db, table='projects', row_model=ProjectRow, organization_id=org_a).create_item(
        {'id': str(id1), 'archived': False, 'organization_id': str(org_a)}
    )
    DatabaseHandler(db, table='projects', row_model=ProjectRow, organization_id=org_a).create_item(
        {'id': str(id2), 'archived': False, 'organization_id': str(org_a)}
    )
    DatabaseHandler(db, table='projects', row_model=ProjectRow, organization_id=org_b).create_item(
        {'id': str(id3), 'archived': False, 'organization_id': str(org_b)}
    )

    crud = DatabaseHandler(db, table='projects', row_model=ProjectRow, organization_id=org_a)
    rows = crud.list_items(
        filters=[
            Filter(
                column='id',
                op='in',
                value=[UUID(str(id2)), UUID(str(id1)), UUID(str(id3))],
            )
        ]
    )
    returned_ids = {row.id for row in rows}
    assert returned_ids == {str(id1), str(id2)}
