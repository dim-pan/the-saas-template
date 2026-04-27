import re
from dataclasses import dataclass
from typing import Any


@dataclass
class TestDbResult:
    __test__ = False
    data: Any


class TestDbQuery:
    __test__ = False

    def __init__(
        self,
        *,
        storage: dict[str, list[dict[str, Any]]],
        table: str,
        op: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._storage = storage
        self._table = table
        self._op = op
        self._payload = payload
        self._eq_filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._gte_filters: list[tuple[str, Any]] = []
        self._lte_filters: list[tuple[str, Any]] = []
        self._ilike_filters: list[tuple[str, str]] = []

    def select(self, _columns: str) -> 'TestDbQuery':
        return TestDbQuery(storage=self._storage, table=self._table, op='select')

    def insert(self, payload: dict[str, Any]) -> 'TestDbQuery':
        return TestDbQuery(
            storage=self._storage,
            table=self._table,
            op='insert',
            payload=payload,
        )

    def update(self, payload: dict[str, Any]) -> 'TestDbQuery':
        return TestDbQuery(
            storage=self._storage,
            table=self._table,
            op='update',
            payload=payload,
        )

    def eq(self, column: str, value: Any) -> 'TestDbQuery':
        self._eq_filters.append((column, value))
        return self

    def in_(self, column: str, values: list[Any]) -> 'TestDbQuery':
        self._in_filters.append((column, values))
        return self

    def gte(self, column: str, value: Any) -> 'TestDbQuery':
        self._gte_filters.append((column, value))
        return self

    def lte(self, column: str, value: Any) -> 'TestDbQuery':
        self._lte_filters.append((column, value))
        return self

    def ilike(self, column: str, pattern: Any) -> 'TestDbQuery':
        self._ilike_filters.append((column, str(pattern)))
        return self

    def filter(self, column: str, operator: str, value: str) -> 'TestDbQuery':
        if operator != 'in':
            raise ValueError("Only 'in' operator supported in test double")
        raw = value.strip()
        if not raw.startswith('(') or not raw.endswith(')'):
            raise ValueError("Expected '(...)' for in filter")
        inner = raw[1:-1]
        values = [] if inner == '' else inner.split(',')
        self._in_filters.append((column, values))
        return self

    def order(self, _column: str, desc: bool = False) -> 'TestDbQuery':
        return self

    def range(self, _from: int, _to: int) -> 'TestDbQuery':
        return self

    def execute(self) -> TestDbResult:
        rows = list(self._storage.get(self._table, []))

        def matches(row: dict[str, Any]) -> bool:
            for column, value in self._eq_filters:
                if row.get(column) != value:
                    return False
            for column, values in self._in_filters:
                current = row.get(column)
                if current not in values:
                    return False
            for column, value in self._gte_filters:
                current = row.get(column)
                if current is None:
                    return False
                try:
                    if current < value:
                        return False
                except TypeError:
                    return False
            for column, value in self._lte_filters:
                current = row.get(column)
                if current is None:
                    return False
                try:
                    if current > value:
                        return False
                except TypeError:
                    return False
            for column, pattern in self._ilike_filters:
                current = row.get(column)
                if current is None:
                    return False
                # Basic Postgres ILIKE emulation: % => .*, _ => . (case-insensitive)
                escaped = re.escape(pattern)
                regex = '^' + escaped.replace(r'\%', '.*').replace(r'\_', '.') + '$'
                if re.match(regex, str(current), flags=re.IGNORECASE) is None:
                    return False
            return True

        if self._op == 'select':
            selected = [row for row in rows if matches(row)]
            return TestDbResult(data=selected)

        if self._op == 'insert':
            if self._payload is None:
                raise ValueError('Missing payload for insert')
            row = dict(self._payload)
            self._storage.setdefault(self._table, []).append(row)
            return TestDbResult(data=[row])

        if self._op == 'update':
            if self._payload is None:
                raise ValueError('Missing payload for update')
            updated: list[dict[str, Any]] = []
            for row in self._storage.get(self._table, []):
                if matches(row):
                    row.update(self._payload)
                    updated.append(dict(row))
            return TestDbResult(data=updated)

        raise ValueError(f'Unknown op: {self._op}')


class TestDbClient:
    __test__ = False

    def __init__(self) -> None:
        self.storage: dict[str, list[dict[str, Any]]] = {}

    def table(self, table: str) -> TestDbQuery:
        return TestDbQuery(storage=self.storage, table=table, op='table')
