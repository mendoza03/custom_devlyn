from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _normalize_pg_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            normalized[key] = value.isoformat()
        elif isinstance(value, memoryview):
            normalized[key] = value.tobytes().decode("utf-8", errors="replace")
        else:
            normalized[key] = value
    return normalized


class BiometricIngestBackend:
    def __init__(self, *, dsn: str, statement_timeout_ms: int, max_pool_size: int = 6):
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=max_pool_size,
            kwargs={
                "autocommit": True,
                "row_factory": dict_row,
                "options": f"-c statement_timeout={statement_timeout_ms}",
            },
            timeout=10,
        )
        self._pool.open(wait=True)

    def healthcheck(self) -> dict[str, Any]:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select current_database() as db, current_user as usr, 1 as ok")
                row = cur.fetchone() or {}
        return _normalize_pg_row(dict(row))

    def fetch_count(self, where_sql: str, params: dict[str, Any], table: str) -> int:
        query = f"select count(*) as total from {table} {where_sql}"
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone() or {}
        return int(row.get("total", 0))

    def fetch_rows(
        self,
        *,
        table: str,
        columns: list[str],
        where_sql: str,
        params: dict[str, Any],
        order_by: str,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        query = (
            f"select {', '.join(columns)} from {table} {where_sql} "
            f"order by {order_by} limit %(limit)s offset %(offset)s"
        )
        bound = dict(params)
        bound.update({"limit": limit, "offset": offset})
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, bound)
                rows = cur.fetchall() or []
        return [_normalize_pg_row(dict(row)) for row in rows]

    def close(self) -> None:
        self._pool.close()
