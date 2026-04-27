from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Generic, Literal, Mapping, TypeVar, overload
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.constants.tables import is_global_table
from supabase import Client


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


RowModelT = TypeVar('RowModelT', bound=BaseModel)
InsertT = TypeVar('InsertT', bound=Mapping[str, Any])
UpdateT = TypeVar('UpdateT', bound=Mapping[str, Any])

FilterOp = Literal['eq', 'in', 'gte', 'lte', 'ilike', 'is']


@dataclass(frozen=True)
class Filter:
    column: str
    op: FilterOp
    value: object


class DatabaseHandler(Generic[RowModelT, InsertT, UpdateT]):
    def __init__(
        self,
        client: Client,
        table: str,
        *,
        row_model: type[RowModelT],
        organization_id: UUID | None = None,
    ) -> None:
        self.client = client
        self.table = table
        # `DatabaseHandler` is generic (RowModelT), but Python erases generics at runtime.
        # We therefore need the concrete Pydantic model class to parse Supabase rows via
        # `row_model.model_validate(...)` and return strongly-typed models from the DB layer.
        self.row_model = row_model
        self.organization_id = organization_id
        self.is_global = is_global_table(table)
        # organization_id may be None when only using get_item(..., require_org=False)

    def _require_org_id(self) -> str | None:
        if self.is_global:
            return None
        if self.organization_id is None:
            raise ValueError(
                f'{self.table}: organization_id is required for org-scoped CRUD operations'
            )
        return str(self.organization_id)

    def _apply_org_scope(self, query: Any) -> Any:
        org_id = self._require_org_id()
        if org_id is None:
            return query
        return query.eq('organization_id', org_id)

    def _parse_row(self, raw: object) -> RowModelT:
        if isinstance(raw, self.row_model):
            return raw
        return self.row_model.model_validate(raw)

    def _supports_archiving(self) -> bool:
        # We only enforce archived=false defaults for tables whose row model declares
        # an `archived` field. This avoids breaking tables that don't implement soft delete.
        model_fields = getattr(self.row_model, 'model_fields', None)
        if not isinstance(model_fields, dict):
            return False
        return 'archived' in model_fields

    def _apply_filters(self, query: Any, filters: list[Filter]) -> Any:
        if self._supports_archiving():
            for filter_item in filters:
                if filter_item.column == 'archived':
                    raise ValueError(
                        f'{self.table}: do not filter by archived explicitly; archived rows are always excluded'
                    )

        for filter_item in filters:
            op = filter_item.op
            column = filter_item.column
            value = self._jsonify_value(filter_item.value)

            if op == 'is':
                is_value = 'null' if value is None else value
                try:
                    query = query.is_(column, is_value)
                except AttributeError:
                    query = query.filter(column, 'is', is_value)
                continue

            if op == 'eq':
                query = query.eq(column, value)
                continue

            if op == 'in':
                if not isinstance(value, (list, tuple, set)):
                    raise ValueError(f"{self.table}: 'in' filter value must be a list/tuple/set")
                values_list = [self._jsonify_value(item) for item in list(value)]
                try:
                    query = query.in_(column, values_list)
                except AttributeError:
                    # fallback for unexpected client API differences
                    query = query.filter(
                        column,
                        'in',
                        f'({",".join([str(item) for item in values_list])})',
                    )
                continue

            if op == 'gte':
                query = query.gte(column, value)
                continue

            if op == 'lte':
                query = query.lte(column, value)
                continue

            if op == 'ilike':
                query = query.ilike(column, value)
                continue

            raise ValueError(f'{self.table}: unsupported filter op: {op}')

        return query

    def _apply_archived_scope(self, query: Any) -> Any:
        if not self._supports_archiving():
            return query
        return query.eq('archived', False)

    # This is needed because Supabase request bodies must be JSON-serializable, but the generated Supabase types use Python-native UUID/datetime.
    def _jsonify_value(self, value: object) -> Any:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, BaseModel):
            return value.model_dump(mode='json')
        if isinstance(value, dict):
            return {str(key): self._jsonify_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._jsonify_value(item) for item in value]
        return value

    def _jsonify_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: self._jsonify_value(value) for key, value in payload.items()}

    def create_item(self, values: InsertT) -> RowModelT:
        # Copy into a mutable object
        payload: dict[str, Any] = dict(values)
        payload['created_at'] = utc_now_iso()
        org_id = self._require_org_id()
        if org_id is not None:
            payload_org = payload.get('organization_id')
            if payload_org is None:
                raise ValueError(
                    f'{self.table}: payload organization_id is required for org-scoped creates'
                )

            payload_org_id = str(payload_org) if isinstance(payload_org, UUID) else payload_org
            if payload_org_id != org_id:
                raise ValueError(
                    f'{self.table}: payload organization_id does not match CRUD organization_id'
                )

        query = self.client.table(self.table).insert(self._jsonify_payload(payload))
        result = query.execute()
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Create failed',
                )
            return self._parse_row(data[0])
        if isinstance(data, dict):
            return self._parse_row(data)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Create failed',
        )

    def list_items(
        self,
        *,
        filters: list[Filter] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'created_at',
        ascending: bool = False,
    ) -> list[RowModelT]:
        if limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='limit must be greater than 0',
            )
        query = self._apply_org_scope(self.client.table(self.table).select('*'))
        query = self._apply_archived_scope(query)
        if filters is not None:
            query = self._apply_filters(query, filters)

        result = (
            query.order(order_by, desc=not ascending)
            .range(offset, offset + max(limit, 0) - 1)
            .execute()
        )
        data = result.data
        if isinstance(data, list):
            return [self._parse_row(row) for row in data]
        if data is None:
            return []
        return [self._parse_row(data)]

    def get_item(
        self,
        value: UUID | str,
        *,
        key: str = 'id',
        require_org: bool = True,
    ) -> RowModelT | None:
        query = self.client.table(self.table).select('*')
        if require_org:
            query = self._apply_org_scope(query)
        result = self._apply_archived_scope(query).eq(key, self._jsonify_value(value)).execute()
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                if require_org:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
                return None
            return self._parse_row(data[0])
        if isinstance(data, dict):
            return self._parse_row(data)
        if require_org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
        return None

    def restore_item(self, entity_id: UUID) -> RowModelT:
        """
        De-archive (restore) a row by setting archived=false.

        This intentionally bypasses the "active-only updates" guard in update_item(),
        since restoring is the only operation allowed on archived rows.
        """

        if not self._supports_archiving():
            raise ValueError(f'{self.table}: restore_item is not supported (no archived)')
        # Bypass the archived=false scope by using a raw update query
        query = self.client.table(self.table).update(
            self._jsonify_payload({'archived': False, 'updated_at': utc_now_iso()})
        )
        query = self._apply_org_scope(query).eq('id', str(entity_id))
        result = query.execute()
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
            return self._parse_row(data[0])
        if isinstance(data, dict):
            return self._parse_row(data)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    @overload
    def update_item(
        self,
        value: UUID,
        values: UpdateT,
        *,
        key: str = 'id',
    ) -> RowModelT: ...

    @overload
    def update_item(
        self,
        value: UUID,
        values: Mapping[str, Any],
        *,
        key: str = 'id',
    ) -> RowModelT: ...

    def update_item(
        self,
        value: UUID,
        values: Mapping[str, Any],
        *,
        key: str = 'id',
    ) -> RowModelT:
        # Copy into a mutable object
        payload: dict[str, Any] = dict(values)
        payload['updated_at'] = utc_now_iso()
        org_id = self._require_org_id()
        if org_id is not None and 'organization_id' in payload:
            payload_org = payload.get('organization_id')
            payload_org_id = str(payload_org) if isinstance(payload_org, UUID) else payload_org
            if payload_org_id != org_id:
                raise ValueError(
                    f'{self.table}: payload organization_id does not match CRUD organization_id'
                )
        query = self.client.table(self.table).update(self._jsonify_payload(payload))
        query = self._apply_org_scope(query)
        query = self._apply_archived_scope(query)
        query = query.eq(key, self._jsonify_value(value))
        result = query.execute()
        data = result.data
        if isinstance(data, list):
            if len(data) == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
            return self._parse_row(data[0])
        if isinstance(data, dict):
            return self._parse_row(data)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')

    def set_archived_item(self, entity_id: UUID, *, archived: bool) -> RowModelT:
        return self.update_item(entity_id, {'archived': archived})

    def delete_item(self, entity_id: UUID) -> RowModelT:
        return self.set_archived_item(entity_id, archived=True)
