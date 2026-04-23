from __future__ import annotations

import atexit
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

if TYPE_CHECKING:
    import psycopg


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT_PATH = ROOT_DIR / "sample_data" / "biometric_snapshot_2026-03-18.json"


@dataclass(slots=True)
class PageResult:
    view: str
    page: int
    page_size: int
    total: int
    items: list[dict[str, Any]]
    filter_options: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "view": self.view,
            "page": self.page,
            "page_size": self.page_size,
            "total": self.total,
            "items": self.items,
            "filter_options": self.filter_options,
        }


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_value(item) for key, item in value.items()}
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _normalize_value(value) for key, value in row.items()}


def _build_filter_options(items: list[dict[str, Any]], view: str) -> dict[str, list[str]]:
    def collect(field: str) -> list[str]:
        values = {
            str(item.get(field))
            for item in items
            if item.get(field) not in (None, "", [])
        }
        return sorted(values)

    if view == "raw_requests":
        return {"event_kind": collect("event_kind_detected")}
    if view == "normalized_events":
        return {"event_kind": collect("event_kind"), "identity_resolution": collect("identity_resolution")}
    if view == "quarantine_events":
        return {"event_kind": collect("event_kind"), "reason": collect("reason")}
    if view == "devices":
        return {"status": collect("status")}
    return {}


class SnapshotDataAccess:
    def __init__(self, snapshot_path: Path):
        self.snapshot_path = snapshot_path
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.payload = payload

    def get_summary(self) -> dict[str, Any]:
        summary = dict(self.payload.get("summary") or {})
        summary["source_mode"] = "snapshot"
        summary["snapshot_path"] = str(self.snapshot_path)
        summary["generated_at_utc"] = self.payload.get("generated_at_utc")
        return summary

    def get_page(
        self,
        *,
        view: str,
        page: int,
        page_size: int,
        search: str,
        filters: dict[str, str],
    ) -> PageResult:
        key = {
            "raw_requests": "raw_requests",
            "normalized_events": "normalized_events",
            "quarantine_events": "quarantine_events",
            "devices": "devices",
        }[view]
        items = list(self.payload.get(key) or [])
        filter_options = _build_filter_options(items, view)
        filtered = self._apply_filters(items, view=view, search=search, filters=filters)
        total = len(filtered)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return PageResult(
            view=view,
            page=page,
            page_size=page_size,
            total=total,
            items=filtered[start:end],
            filter_options=filter_options,
        )

    def get_record(self, *, view: str, record_id: str) -> dict[str, Any] | None:
        key = {
            "raw_requests": "raw_requests",
            "normalized_events": "normalized_events",
            "quarantine_events": "quarantine_events",
            "devices": "devices",
        }[view]
        items = list(self.payload.get(key) or [])
        id_field = "device_id" if view == "devices" else "id"
        for item in items:
            if str(item.get(id_field)) == record_id:
                return item
        return None

    def _apply_filters(
        self,
        items: list[dict[str, Any]],
        *,
        view: str,
        search: str,
        filters: dict[str, str],
    ) -> list[dict[str, Any]]:
        search_lower = search.strip().lower()
        filtered: list[dict[str, Any]] = []
        for item in items:
            if filters:
                if view == "raw_requests" and filters.get("event_kind"):
                    if item.get("event_kind_detected") != filters["event_kind"]:
                        continue
                if view == "normalized_events":
                    if filters.get("event_kind") and item.get("event_kind") != filters["event_kind"]:
                        continue
                    if filters.get("identity_resolution") and item.get("identity_resolution") != filters["identity_resolution"]:
                        continue
                if view == "quarantine_events":
                    if filters.get("event_kind") and item.get("event_kind") != filters["event_kind"]:
                        continue
                    if filters.get("reason") and item.get("reason") != filters["reason"]:
                        continue
                if view == "devices" and filters.get("status"):
                    if item.get("status") != filters["status"]:
                        continue

            if search_lower:
                haystack = json.dumps(item, ensure_ascii=False, default=_json_default).lower()
                if search_lower not in haystack:
                    continue
            filtered.append(item)

        sort_field = {
            "raw_requests": "received_at_utc",
            "normalized_events": "event_occurred_at_utc",
            "quarantine_events": "raw_received_at_utc",
            "devices": "last_seen_at",
        }[view]
        filtered.sort(key=lambda item: str(item.get(sort_field) or ""), reverse=True)
        return filtered


class SSHTunnel:
    def __init__(self, ssh_target: str, remote_host: str, remote_port: int):
        self.ssh_target = ssh_target
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port: int | None = None
        self.process: subprocess.Popen[str] | None = None
        atexit.register(self.close)

    def _allocate_local_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _is_port_open(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex(("127.0.0.1", port)) == 0

    def ensure(self) -> int:
        if self.process and self.process.poll() is None and self.local_port and self._is_port_open(self.local_port):
            return self.local_port

        self.close()
        self.local_port = self._allocate_local_port()
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-N",
            "-L",
            f"127.0.0.1:{self.local_port}:{self.remote_host}:{self.remote_port}",
            self.ssh_target,
        ]
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 10
        while time.time() < deadline:
            if self.process.poll() is not None:
                stderr = (self.process.stderr.read() if self.process.stderr else "").strip()
                raise RuntimeError(f"SSH tunnel failed to start: {stderr or 'unknown error'}")
            if self._is_port_open(self.local_port):
                return self.local_port
            time.sleep(0.1)
        raise RuntimeError("SSH tunnel did not become ready in time")

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.process = None
        self.local_port = None


class PostgresDataAccess:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing PostgreSQL driver. Install dashboard dependencies with "
                "`python3 -m pip install --user -r dashboard/requirements.txt`."
            ) from exc

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def get_summary(self) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            counts: dict[str, Any] = {}
            cur.execute(
                """
                SELECT
                    (SELECT count(*) FROM raw_request) AS raw_requests,
                    (SELECT count(*) FROM normalized_event) AS normalized_events,
                    (SELECT count(*) FROM event_quarantine) AS quarantine_events,
                    (SELECT count(*) FROM processing_error) AS processing_errors,
                    (SELECT count(*) FROM device_registry) AS devices,
                    (SELECT count(*) FROM raw_request r
                        LEFT JOIN normalized_event n ON n.raw_request_id = r.id
                        LEFT JOIN event_quarantine q ON q.raw_request_id = r.id
                     WHERE n.raw_request_id IS NULL AND q.raw_request_id IS NULL) AS unclassified_raw_requests,
                    (SELECT min(received_at_utc) FROM raw_request) AS raw_first_received_at,
                    (SELECT max(received_at_utc) FROM raw_request) AS raw_last_received_at,
                    (SELECT min(event_occurred_at_utc) FROM normalized_event) AS normalized_first_event_at,
                    (SELECT max(event_occurred_at_utc) FROM normalized_event) AS normalized_last_event_at
                """
            )
            counts = _normalize_row(cur.fetchone() or {})

            cur.execute(
                """
                SELECT event_kind_detected AS label, count(*)
                FROM raw_request
                GROUP BY 1
                ORDER BY 2 DESC, 1
                """
            )
            raw_by_kind = [_normalize_row(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT event_kind AS label, count(*)
                FROM normalized_event
                GROUP BY 1
                ORDER BY 2 DESC, 1
                """
            )
            normalized_by_kind = [_normalize_row(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT reason, event_kind, count(*)
                FROM event_quarantine
                GROUP BY 1, 2
                ORDER BY 3 DESC, 1, 2
                """
            )
            quarantine_by_reason = [_normalize_row(row) for row in cur.fetchall()]

            cur.execute(
                """
                SELECT status AS label, count(*)
                FROM device_status
                GROUP BY 1
                ORDER BY 2 DESC, 1
                """
            )
            device_status_counts = [_normalize_row(row) for row in cur.fetchall()]

        return {
            "source_mode": "postgres",
            "generated_at_utc": datetime.utcnow().isoformat() + "Z",
            "counts": counts,
            "raw_by_kind": raw_by_kind,
            "normalized_by_kind": normalized_by_kind,
            "quarantine_by_reason": quarantine_by_reason,
            "device_status_counts": device_status_counts,
        }

    def get_page(
        self,
        *,
        view: str,
        page: int,
        page_size: int,
        search: str,
        filters: dict[str, str],
    ) -> PageResult:
        handler = {
            "raw_requests": self._get_raw_requests,
            "normalized_events": self._get_normalized_events,
            "quarantine_events": self._get_quarantine_events,
            "devices": self._get_devices,
        }[view]
        items, total, filter_options = handler(page=page, page_size=page_size, search=search, filters=filters)
        return PageResult(
            view=view,
            page=page,
            page_size=page_size,
            total=total,
            items=items,
            filter_options=filter_options,
        )

    def get_record(self, *, view: str, record_id: str) -> dict[str, Any] | None:
        handler = {
            "raw_requests": self._get_raw_request_record,
            "normalized_events": self._get_normalized_event_record,
            "quarantine_events": self._get_quarantine_event_record,
            "devices": self._get_device_event_record,
        }[view]
        return handler(record_id)

    def _build_like(self, fields: list[str], search: str) -> tuple[str, list[Any]]:
        if not search.strip():
            return "", []
        clause = " OR ".join(f"{field} ILIKE %s" for field in fields)
        params = [f"%{search.strip()}%"] * len(fields)
        return f" AND ({clause})", params

    def _fetch_filter_options(self, sql_text: str, params: list[Any] | None = None) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql_text, params or [])
            return [str(row["value"]) for row in cur.fetchall() if row["value"] not in (None, "")]

    def _get_raw_requests(self, *, page: int, page_size: int, search: str, filters: dict[str, str]) -> tuple[list[dict[str, Any]], int, dict[str, list[str]]]:
        where = ["TRUE"]
        params: list[Any] = []
        if filters.get("event_kind"):
            where.append("event_kind_detected = %s")
            params.append(filters["event_kind"])
        like_sql, like_params = self._build_like(
            [
                "COALESCE(source_ip::text, '')",
                "path",
                "event_kind_detected",
                "COALESCE(device_id_hint, '')",
                "COALESCE(body_raw, '')",
            ],
            search,
        )
        with self._connect() as conn, conn.cursor() as cur:
            base_where = " AND ".join(where)
            count_sql = f"SELECT count(*) AS total FROM raw_request WHERE {base_where}{like_sql}"
            cur.execute(count_sql, params + like_params)
            total = int(cur.fetchone()["total"])

            data_sql = f"""
                SELECT
                    id,
                    received_at_utc,
                    ingest_id,
                    source_ip::text AS source_ip,
                    source_port,
                    listener_port,
                    method,
                    path,
                    query,
                    headers_jsonb,
                    body_jsonb,
                    body_raw,
                    payload_hash,
                    event_kind_detected,
                    device_id_hint,
                    device_model_hint,
                    created_at
                FROM raw_request
                WHERE {base_where}{like_sql}
                ORDER BY received_at_utc DESC, id DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, params + like_params + [page_size, (page - 1) * page_size])
            items = [_normalize_row(row) for row in cur.fetchall()]

        filter_options = {
            "event_kind": self._fetch_filter_options(
                """
                SELECT DISTINCT event_kind_detected AS value
                FROM raw_request
                ORDER BY 1
                """
            )
        }
        return items, total, filter_options

    def _get_normalized_events(self, *, page: int, page_size: int, search: str, filters: dict[str, str]) -> tuple[list[dict[str, Any]], int, dict[str, list[str]]]:
        where = ["event_kind = 'access_control'", "COALESCE(user_id_on_device, '') <> ''"]
        params: list[Any] = []
        if filters.get("identity_resolution"):
            where.append("identity_resolution = %s")
            params.append(filters["identity_resolution"])
        like_sql, like_params = self._build_like(
            [
                "COALESCE(device_id_resolved, '')",
                "COALESCE(user_id_on_device, '')",
                "COALESCE(card_name, '')",
                "COALESCE(door_name, '')",
                "COALESCE(body_jsonb::text, '')",
            ],
            search,
        )
        with self._connect() as conn, conn.cursor() as cur:
            base_where = " AND ".join(where)
            count_sql = f"SELECT count(*) AS total FROM normalized_event WHERE {base_where}{like_sql}"
            cur.execute(count_sql, params + like_params)
            total = int(cur.fetchone()["total"])

            data_sql = f"""
                SELECT
                    id,
                    raw_request_id,
                    raw_received_at_utc,
                    event_occurred_at_utc,
                    event_kind,
                    device_id_resolved,
                    source_ip::text AS source_ip,
                    listener_port,
                    user_id_on_device,
                    card_name,
                    door_name,
                    direction,
                    granted,
                    error_code,
                    method_code,
                    reader_id,
                    card_no,
                    user_type_code,
                    door_index,
                    block_id,
                    stream_index,
                    dedup_key,
                    identity_resolution,
                    body_jsonb,
                    created_at
                FROM normalized_event
                WHERE {base_where}{like_sql}
                ORDER BY event_occurred_at_utc DESC, id DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, params + like_params + [page_size, (page - 1) * page_size])
            items = [_normalize_row(row) for row in cur.fetchall()]

        filter_options = {
            "identity_resolution": self._fetch_filter_options(
                """
                SELECT DISTINCT identity_resolution AS value
                FROM normalized_event
                WHERE event_kind = 'access_control'
                  AND COALESCE(user_id_on_device, '') <> ''
                ORDER BY 1
                """
            ),
        }
        return items, total, filter_options

    def _get_quarantine_events(self, *, page: int, page_size: int, search: str, filters: dict[str, str]) -> tuple[list[dict[str, Any]], int, dict[str, list[str]]]:
        where = ["TRUE"]
        params: list[Any] = []
        if filters.get("event_kind"):
            where.append("event_kind = %s")
            params.append(filters["event_kind"])
        if filters.get("reason"):
            where.append("reason = %s")
            params.append(filters["reason"])
        like_sql, like_params = self._build_like(
            [
                "event_kind",
                "reason",
                "COALESCE(candidate_device_id, '')",
                "COALESCE(body_jsonb::text, '')",
            ],
            search,
        )
        with self._connect() as conn, conn.cursor() as cur:
            base_where = " AND ".join(where)
            count_sql = f"SELECT count(*) AS total FROM event_quarantine WHERE {base_where}{like_sql}"
            cur.execute(count_sql, params + like_params)
            total = int(cur.fetchone()["total"])

            data_sql = f"""
                SELECT
                    id,
                    raw_request_id,
                    raw_received_at_utc,
                    source_ip::text AS source_ip,
                    listener_port,
                    payload_hash,
                    reason,
                    candidate_device_id,
                    event_kind,
                    body_jsonb,
                    created_at
                FROM event_quarantine
                WHERE {base_where}{like_sql}
                ORDER BY raw_received_at_utc DESC, id DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, params + like_params + [page_size, (page - 1) * page_size])
            items = [_normalize_row(row) for row in cur.fetchall()]

        filter_options = {
            "event_kind": self._fetch_filter_options(
                """
                SELECT DISTINCT event_kind AS value
                FROM event_quarantine
                ORDER BY 1
                """
            ),
            "reason": self._fetch_filter_options(
                """
                SELECT DISTINCT reason AS value
                FROM event_quarantine
                ORDER BY 1
                """
            ),
        }
        return items, total, filter_options

    def _get_devices(self, *, page: int, page_size: int, search: str, filters: dict[str, str]) -> tuple[list[dict[str, Any]], int, dict[str, list[str]]]:
        where = ["r.event_kind_detected IN ('door_status', 'heartbeat_connect', 'unknown')"]
        params: list[Any] = []
        if filters.get("event_kind"):
            where.append("r.event_kind_detected = %s")
            params.append(filters["event_kind"])
        if filters.get("outcome"):
            if filters["outcome"] == "normalized":
                where.append("n.raw_request_id IS NOT NULL")
            elif filters["outcome"] == "quarantine":
                where.append("q.raw_request_id IS NOT NULL")
            elif filters["outcome"] == "raw_only":
                where.append("n.raw_request_id IS NULL AND q.raw_request_id IS NULL")
        like_sql, like_params = self._build_like(
            [
                "COALESCE(r.source_ip::text, '')",
                "COALESCE(r.path, '')",
                "COALESCE(r.device_id_hint, '')",
                "COALESCE(n.device_id_resolved, '')",
                "COALESCE(q.candidate_device_id, '')",
                "COALESCE(q.reason, '')",
                "COALESCE(r.body_jsonb::text, '')",
            ],
            search,
        )
        with self._connect() as conn, conn.cursor() as cur:
            base_where = " AND ".join(where)
            count_sql = f"""
                SELECT count(*) AS total
                FROM raw_request r
                LEFT JOIN normalized_event n ON n.raw_request_id = r.id
                LEFT JOIN event_quarantine q ON q.raw_request_id = r.id
                WHERE {base_where}{like_sql}
            """
            cur.execute(count_sql, params + like_params)
            total = int(cur.fetchone()["total"])

            data_sql = f"""
                SELECT
                    r.id,
                    r.received_at_utc,
                    r.source_ip::text AS source_ip,
                    r.listener_port,
                    r.method,
                    r.path,
                    r.event_kind_detected,
                    r.device_id_hint,
                    r.device_model_hint,
                    n.device_id_resolved,
                    n.identity_resolution,
                    q.candidate_device_id,
                    q.reason,
                    CASE
                        WHEN n.raw_request_id IS NOT NULL THEN 'normalized'
                        WHEN q.raw_request_id IS NOT NULL THEN 'quarantine'
                        ELSE 'raw_only'
                    END AS outcome,
                    r.body_jsonb,
                    r.headers_jsonb,
                    r.body_raw,
                    r.created_at
                FROM raw_request r
                LEFT JOIN normalized_event n ON n.raw_request_id = r.id
                LEFT JOIN event_quarantine q ON q.raw_request_id = r.id
                WHERE {base_where}{like_sql}
                ORDER BY r.received_at_utc DESC, r.id DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(data_sql, params + like_params + [page_size, (page - 1) * page_size])
            items = [_normalize_row(row) for row in cur.fetchall()]

        filter_options = {
            "event_kind": self._fetch_filter_options(
                """
                SELECT DISTINCT event_kind_detected AS value
                FROM raw_request
                WHERE event_kind_detected IN ('door_status', 'heartbeat_connect', 'unknown')
                ORDER BY 1
                """
            ),
            "outcome": ["normalized", "quarantine", "raw_only"],
        }
        return items, total, filter_options

    def _fetch_one(self, sql_text: str, params: list[Any]) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql_text, params)
            row = cur.fetchone()
            return _normalize_row(row) if row else None

    def _get_raw_request_record(self, record_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT
                id,
                received_at_utc,
                ingest_id,
                source_ip::text AS source_ip,
                source_port,
                listener_port,
                method,
                path,
                query,
                headers_jsonb,
                body_jsonb,
                body_raw,
                payload_hash,
                event_kind_detected,
                device_id_hint,
                device_model_hint,
                created_at
            FROM raw_request
            WHERE id = %s
            """,
            [record_id],
        )

    def _get_normalized_event_record(self, record_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT
                id,
                raw_request_id,
                raw_received_at_utc,
                event_occurred_at_utc,
                event_kind,
                device_id_resolved,
                source_ip::text AS source_ip,
                listener_port,
                user_id_on_device,
                card_name,
                door_name,
                direction,
                granted,
                error_code,
                method_code,
                reader_id,
                card_no,
                user_type_code,
                door_index,
                block_id,
                stream_index,
                dedup_key,
                identity_resolution,
                body_jsonb,
                created_at
            FROM normalized_event
            WHERE id = %s
            """,
            [record_id],
        )

    def _get_quarantine_event_record(self, record_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT
                id,
                raw_request_id,
                raw_received_at_utc,
                source_ip::text AS source_ip,
                listener_port,
                payload_hash,
                reason,
                candidate_device_id,
                event_kind,
                body_jsonb,
                created_at
            FROM event_quarantine
            WHERE id = %s
            """,
            [record_id],
        )

    def _get_device_event_record(self, record_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            SELECT
                r.id,
                r.received_at_utc,
                r.ingest_id,
                r.source_ip::text AS source_ip,
                r.source_port,
                r.listener_port,
                r.method,
                r.path,
                r.query,
                r.headers_jsonb,
                r.body_jsonb,
                r.body_raw,
                r.payload_hash,
                r.event_kind_detected,
                r.device_id_hint,
                r.device_model_hint,
                n.id AS normalized_event_id,
                n.device_id_resolved,
                n.identity_resolution,
                q.id AS quarantine_id,
                q.candidate_device_id,
                q.reason,
                CASE
                    WHEN n.raw_request_id IS NOT NULL THEN 'normalized'
                    WHEN q.raw_request_id IS NOT NULL THEN 'quarantine'
                    ELSE 'raw_only'
                END AS outcome,
                r.created_at
            FROM raw_request r
            LEFT JOIN normalized_event n ON n.raw_request_id = r.id
            LEFT JOIN event_quarantine q ON q.raw_request_id = r.id
            WHERE r.id = %s
              AND r.event_kind_detected IN ('door_status', 'heartbeat_connect', 'unknown')
            """,
            [record_id],
        )


class SSHTunnelPostgresDataAccess(PostgresDataAccess):
    def __init__(
        self,
        *,
        ssh_target: str,
        remote_env_path: str,
        remote_host: str,
        remote_port: int,
        database_url: str = "",
    ):
        self.ssh_target = ssh_target
        self.remote_env_path = remote_env_path
        self.remote_host = remote_host
        self.remote_port = remote_port
        self._remote_database_url = database_url or self._fetch_remote_database_url()
        self._tunnel = SSHTunnel(ssh_target=ssh_target, remote_host=remote_host, remote_port=remote_port)
        super().__init__(database_url=self._with_local_port(self._remote_database_url, self._tunnel.ensure()))

    def _fetch_remote_database_url(self) -> str:
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            self.ssh_target,
            f"grep '^BIOMETRIC_DATABASE_URL=' {self.remote_env_path} | tail -n 1 | cut -d= -f2-",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        database_url = result.stdout.strip()
        if not database_url:
            raise RuntimeError(f"Could not read BIOMETRIC_DATABASE_URL from {self.remote_env_path} on {self.ssh_target}")
        return database_url

    def get_summary(self) -> dict[str, Any]:
        summary = super().get_summary()
        summary["source_mode"] = "ssh_tunnel"
        summary["ssh_target"] = self.ssh_target
        return summary

    def _with_local_port(self, database_url: str, local_port: int) -> str:
        parsed = urlsplit(database_url)
        if not parsed.scheme or not parsed.hostname:
            raise RuntimeError(f"Invalid database URL: {database_url}")
        netloc = parsed.netloc
        if "@" in netloc:
            credentials, _ = netloc.rsplit("@", 1)
            new_netloc = f"{credentials}@127.0.0.1:{local_port}"
        else:
            new_netloc = f"127.0.0.1:{local_port}"
        rebuilt = SplitResult(
            scheme=parsed.scheme,
            netloc=new_netloc,
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
        )
        return urlunsplit(rebuilt)

    def _connect(self):
        self.database_url = self._with_local_port(self._remote_database_url, self._tunnel.ensure())
        return super()._connect()


def create_data_access() -> SnapshotDataAccess | PostgresDataAccess:
    source = os.getenv("DAHUA_DASHBOARD_SOURCE", "ssh_tunnel").strip().lower()
    if source == "ssh_tunnel":
        return SSHTunnelPostgresDataAccess(
            ssh_target=os.getenv("DAHUA_DASHBOARD_SSH_TARGET", "root@52.6.240.186").strip(),
            remote_env_path=os.getenv("DAHUA_DASHBOARD_REMOTE_ENV_PATH", "/etc/biometric-ingest.env").strip(),
            remote_host=os.getenv("DAHUA_DASHBOARD_REMOTE_DB_HOST", "127.0.0.1").strip(),
            remote_port=int(os.getenv("DAHUA_DASHBOARD_REMOTE_DB_PORT", "5432").strip()),
            database_url=os.getenv("DAHUA_DASHBOARD_DATABASE_URL", "").strip(),
        )
    if source == "postgres":
        database_url = os.getenv("DAHUA_DASHBOARD_DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("DAHUA_DASHBOARD_DATABASE_URL is required when DAHUA_DASHBOARD_SOURCE=postgres")
        return PostgresDataAccess(database_url)

    snapshot_path = Path(os.getenv("DAHUA_DASHBOARD_SNAPSHOT_PATH", str(DEFAULT_SNAPSHOT_PATH))).expanduser()
    if not snapshot_path.exists():
        raise RuntimeError(f"Snapshot file not found: {snapshot_path}")
    return SnapshotDataAccess(snapshot_path)
