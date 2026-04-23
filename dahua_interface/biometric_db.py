from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from biometric_common import (
    Settings,
    compute_dedup_key,
    epoch_to_datetime,
    normalize_direction,
    normalize_granted,
    parse_int,
    select_event_epoch,
    utc_now,
)


SCHEMA_PATH = Path(__file__).with_name("biometric_schema.sql")


@dataclass(slots=True)
class RawInsertResult:
    raw_request_id: int
    received_at_utc: datetime
    inserted: bool


@dataclass(slots=True)
class ResolutionResult:
    device_id: str | None
    identity_resolution: str
    candidate_device_id: str | None = None


class BiometricDatabase:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.conn = psycopg.connect(settings.database_url)
        self.conn.autocommit = False

    def close(self) -> None:
        self.conn.close()

    def ensure_schema(self) -> None:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(schema_sql)
                self._ensure_partition(cur, "raw_request", utc_now())
                self._ensure_partition(cur, "normalized_event", utc_now())

    def _partition_name(self, table_name: str, value: datetime) -> str:
        return f"{table_name}_{value.strftime('%Y%m')}"

    def _partition_bounds(self, value: datetime) -> tuple[datetime, datetime]:
        start = value.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    def _ensure_partition(self, cur: psycopg.Cursor[Any], table_name: str, value: datetime) -> None:
        partition_name = self._partition_name(table_name, value)
        start, end = self._partition_bounds(value)
        cur.execute(
            """
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = %s AND n.nspname = current_schema()
            """,
            (partition_name,),
        )
        if cur.fetchone():
            return

        cur.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF {table_name}
                FOR VALUES FROM ({start}) TO ({end})
                """
            ).format(
                partition_name=sql.Identifier(partition_name),
                table_name=sql.Identifier(table_name),
                start=sql.Literal(start),
                end=sql.Literal(end),
            )
        )

    def process_spooled_event(self, event: dict[str, Any]) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                raw_result = self._insert_raw_request(cur, event)
                self._process_normalization(cur, event, raw_result)

    def refresh_device_statuses(self) -> None:
        now = utc_now()
        stale_delta = timedelta(seconds=self.settings.stale_after_seconds)
        offline_delta = timedelta(seconds=self.settings.offline_after_seconds)

        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE device_status
                    SET
                        status = CASE
                            WHEN last_heartbeat_at IS NULL THEN status
                            WHEN %s - last_heartbeat_at >= %s THEN 'offline'
                            WHEN %s - last_heartbeat_at >= %s THEN 'stale'
                            ELSE 'online'
                        END,
                        stale_since = CASE
                            WHEN last_heartbeat_at IS NULL THEN stale_since
                            WHEN %s - last_heartbeat_at >= %s THEN COALESCE(stale_since, last_heartbeat_at + %s)
                            WHEN %s - last_heartbeat_at >= %s THEN COALESCE(stale_since, last_heartbeat_at + %s)
                            ELSE NULL
                        END,
                        offline_since = CASE
                            WHEN last_heartbeat_at IS NULL THEN offline_since
                            WHEN %s - last_heartbeat_at >= %s THEN COALESCE(offline_since, last_heartbeat_at + %s)
                            ELSE NULL
                        END,
                        updated_at = %s
                    """,
                    (
                        now,
                        offline_delta,
                        now,
                        stale_delta,
                        now,
                        offline_delta,
                        stale_delta,
                        now,
                        stale_delta,
                        stale_delta,
                        now,
                        offline_delta,
                        offline_delta,
                        now,
                    ),
                )
                cur.execute(
                    """
                    UPDATE device_registry AS reg
                    SET
                        status = stat.status,
                        updated_at = %s
                    FROM device_status AS stat
                    WHERE stat.device_id = reg.device_id
                    """,
                    (now,),
                )

    def _insert_raw_request(self, cur: psycopg.Cursor[Any], event: dict[str, Any]) -> RawInsertResult:
        ingest_id = event["ingest_id"]
        cur.execute(
            """
            SELECT raw_request_id, received_at_utc
            FROM raw_request_registry
            WHERE ingest_id = %s
            """,
            (ingest_id,),
        )
        row = cur.fetchone()
        if row:
            return RawInsertResult(raw_request_id=row[0], received_at_utc=row[1], inserted=False)

        received_at_utc = datetime.fromisoformat(event["received_at_utc"])
        self._ensure_partition(cur, "raw_request", received_at_utc)

        cur.execute(
            """
            INSERT INTO raw_request (
                received_at_utc,
                ingest_id,
                source_ip,
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
                device_model_hint
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                received_at_utc,
                ingest_id,
                event.get("source_ip"),
                event.get("source_port"),
                event.get("listener_port"),
                event.get("method"),
                event.get("path"),
                event.get("query") or "",
                Jsonb(event.get("headers") or {}),
                Jsonb(event.get("body")),
                event.get("body_raw"),
                event.get("payload_hash"),
                event.get("event_kind_detected"),
                event.get("device_id_hint"),
                event.get("device_model_hint"),
            ),
        )
        raw_request_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO raw_request_registry (
                ingest_id,
                received_at_utc,
                raw_request_id,
                payload_hash
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                ingest_id,
                received_at_utc,
                raw_request_id,
                event.get("payload_hash"),
            ),
        )
        return RawInsertResult(raw_request_id=raw_request_id, received_at_utc=received_at_utc, inserted=True)

    def _process_normalization(
        self,
        cur: psycopg.Cursor[Any],
        event: dict[str, Any],
        raw_result: RawInsertResult,
    ) -> None:
        event_kind = event.get("event_kind_detected") or "unknown"
        body = event.get("body")
        body_dict = body if isinstance(body, dict) else None
        event_occurred_at = epoch_to_datetime(select_event_epoch(body_dict)) or raw_result.received_at_utc
        self._ensure_partition(cur, "normalized_event", event_occurred_at)

        resolution = self._resolve_device_id(cur, event, body_dict, event_kind, event_occurred_at)

        data_dict = body_dict.get("Data") if isinstance(body_dict, dict) else None
        user_id_raw = data_dict.get("UserID") if isinstance(data_dict, dict) else None
        has_user_id = bool(str(user_id_raw).strip()) if user_id_raw is not None else False

        # AccessControl is valid without resolved device_id, but only when
        # the payload includes a usable UserID. Denied/anonymous attempts
        # without UserID remain in quarantine for later analysis.
        if event_kind == "access_control" and not has_user_id:
            self._insert_quarantine(
                cur,
                raw_request_id=raw_result.raw_request_id,
                raw_received_at_utc=raw_result.received_at_utc,
                source_ip=event.get("source_ip"),
                listener_port=event.get("listener_port"),
                payload_hash=event.get("payload_hash"),
                reason="missing_user_id",
                candidate_device_id=resolution.device_id or resolution.candidate_device_id,
                event_kind=event_kind,
                body=body,
            )
            return

        can_normalize_without_device = event_kind == "access_control" and has_user_id

        if resolution.device_id is None and not can_normalize_without_device:
            self._insert_quarantine(
                cur,
                raw_request_id=raw_result.raw_request_id,
                raw_received_at_utc=raw_result.received_at_utc,
                source_ip=event.get("source_ip"),
                listener_port=event.get("listener_port"),
                payload_hash=event.get("payload_hash"),
                reason=resolution.identity_resolution,
                candidate_device_id=resolution.candidate_device_id,
                event_kind=event_kind,
                body=body,
            )
            return

        normalized_payload = self._build_normalized_payload(
            raw_request_id=raw_result.raw_request_id,
            raw_received_at_utc=raw_result.received_at_utc,
            event=event,
            body=body_dict,
            event_kind=event_kind,
            event_occurred_at=event_occurred_at,
            resolved_device_id=resolution.device_id,
            identity_resolution=resolution.identity_resolution,
        )
        normalized_event_id = self._insert_normalized_event(cur, normalized_payload)

        if event_kind == "heartbeat_connect" and resolution.device_id:
            self._upsert_device_on_heartbeat(
                cur,
                device_id=resolution.device_id,
                device_model=event.get("device_model_hint"),
                source_ip=event.get("source_ip"),
                listener_port=event.get("listener_port"),
                event_occurred_at=event_occurred_at,
            )
            return

        if resolution.device_id:
            self._touch_device_for_business_event(
                cur,
                device_id=resolution.device_id,
                event_kind=event_kind,
                source_ip=event.get("source_ip"),
                listener_port=event.get("listener_port"),
                event_occurred_at=event_occurred_at,
            )
            if event_kind in {"access_control", "door_status"}:
                self._enqueue_outbox(cur, normalized_event_id, normalized_payload)

    def _resolve_device_id(
        self,
        cur: psycopg.Cursor[Any],
        event: dict[str, Any],
        body: dict[str, Any] | None,
        event_kind: str,
        event_occurred_at: datetime,
    ) -> ResolutionResult:
        device_id_hint = event.get("device_id_hint")
        if event_kind == "heartbeat_connect":
            if device_id_hint:
                return ResolutionResult(device_id=device_id_hint, identity_resolution="heartbeat_payload")
            return ResolutionResult(device_id=None, identity_resolution="heartbeat_missing_device_id")

        if device_id_hint:
            return ResolutionResult(device_id=device_id_hint, identity_resolution="request_path_device_hint")

        source_ip = event.get("source_ip")
        listener_port = event.get("listener_port")
        if not source_ip or listener_port is None:
            return ResolutionResult(device_id=None, identity_resolution="missing_network_identity")

        window_start = event_occurred_at - timedelta(seconds=self.settings.heartbeat_window_seconds)
        cur.execute(
            """
            SELECT device_id, last_heartbeat_at
            FROM device_registry
            WHERE
                last_source_ip = %s
                AND last_listener_port = %s
                AND last_heartbeat_at IS NOT NULL
                AND last_heartbeat_at >= %s
            ORDER BY last_heartbeat_at DESC
            LIMIT 5
            """,
            (source_ip, listener_port, window_start),
        )
        rows = cur.fetchall()
        if not rows:
            return ResolutionResult(device_id=None, identity_resolution="no_recent_heartbeat")

        distinct_devices = {row[0] for row in rows if row[0]}
        if len(distinct_devices) == 1:
            return ResolutionResult(device_id=rows[0][0], identity_resolution="recent_heartbeat")

        return ResolutionResult(
            device_id=None,
            identity_resolution="ambiguous_recent_heartbeat",
            candidate_device_id=rows[0][0],
        )

    def _build_normalized_payload(
        self,
        *,
        raw_request_id: int,
        raw_received_at_utc: datetime,
        event: dict[str, Any],
        body: dict[str, Any] | None,
        event_kind: str,
        event_occurred_at: datetime,
        resolved_device_id: str | None,
        identity_resolution: str,
    ) -> dict[str, Any]:
        data = body.get("Data") if isinstance(body, dict) and isinstance(body.get("Data"), dict) else {}
        user_id_on_device = data.get("UserID")
        card_name = data.get("CardName")
        door_name = data.get("Name")
        direction = normalize_direction(data.get("Type"))
        granted = normalize_granted(data.get("Status"))
        error_code = parse_int(data.get("ErrorCode"))
        method_code = parse_int(data.get("Method"))
        user_type_code = parse_int(data.get("UserType"))
        door_index = parse_int(data.get("Door"))
        block_id = parse_int(data.get("BlockId"))
        stream_index = parse_int(body.get("Index") if isinstance(body, dict) else None)
        dedup_key = compute_dedup_key(
            event_kind=event_kind,
            device_id=resolved_device_id,
            block_id=block_id,
            event_occurred_at=event_occurred_at,
            user_id_on_device=user_id_on_device,
            reader_id=data.get("ReaderID"),
            door_name=door_name,
            method_code=method_code,
            granted=granted,
        )

        return {
            "raw_request_id": raw_request_id,
            "raw_received_at_utc": raw_received_at_utc,
            "event_occurred_at_utc": event_occurred_at,
            "event_kind": event_kind,
            "device_id_resolved": resolved_device_id,
            "source_ip": event.get("source_ip"),
            "listener_port": event.get("listener_port"),
            "user_id_on_device": user_id_on_device,
            "card_name": card_name,
            "door_name": door_name,
            "direction": direction,
            "granted": granted,
            "error_code": error_code,
            "method_code": method_code,
            "reader_id": data.get("ReaderID"),
            "card_no": data.get("CardNo"),
            "user_type_code": user_type_code,
            "door_index": door_index,
            "block_id": block_id,
            "stream_index": stream_index,
            "body_jsonb": body,
            "dedup_key": dedup_key,
            "identity_resolution": identity_resolution,
        }

    def _insert_normalized_event(self, cur: psycopg.Cursor[Any], payload: dict[str, Any]) -> int:
        dedup_key = payload["dedup_key"]
        cur.execute(
            """
            SELECT normalized_event_id
            FROM normalized_event_registry
            WHERE dedup_key = %s
            """,
            (dedup_key,),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO normalized_event (
                raw_request_id,
                raw_received_at_utc,
                event_occurred_at_utc,
                event_kind,
                device_id_resolved,
                source_ip,
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
                body_jsonb,
                dedup_key,
                identity_resolution
            )
            VALUES (
                %(raw_request_id)s,
                %(raw_received_at_utc)s,
                %(event_occurred_at_utc)s,
                %(event_kind)s,
                %(device_id_resolved)s,
                %(source_ip)s,
                %(listener_port)s,
                %(user_id_on_device)s,
                %(card_name)s,
                %(door_name)s,
                %(direction)s,
                %(granted)s,
                %(error_code)s,
                %(method_code)s,
                %(reader_id)s,
                %(card_no)s,
                %(user_type_code)s,
                %(door_index)s,
                %(block_id)s,
                %(stream_index)s,
                %(body_jsonb)s,
                %(dedup_key)s,
                %(identity_resolution)s
            )
            RETURNING id
            """,
            {
                **payload,
                "body_jsonb": Jsonb(payload.get("body_jsonb")),
            },
        )
        normalized_event_id = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO normalized_event_registry (
                dedup_key,
                event_occurred_at_utc,
                normalized_event_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                dedup_key,
                payload["event_occurred_at_utc"],
                normalized_event_id,
            ),
        )
        return normalized_event_id

    def _upsert_device_on_heartbeat(
        self,
        cur: psycopg.Cursor[Any],
        *,
        device_id: str,
        device_model: str | None,
        source_ip: str | None,
        listener_port: int | None,
        event_occurred_at: datetime,
    ) -> None:
        cur.execute(
            """
            SELECT last_heartbeat_at
            FROM device_status
            WHERE device_id = %s
            """,
            (device_id,),
        )
        row = cur.fetchone()
        previous_heartbeat = row[0] if row else None
        heartbeat_interval = None
        if previous_heartbeat is not None:
            heartbeat_interval = max(1, int((event_occurred_at - previous_heartbeat).total_seconds()))

        cur.execute(
            """
            INSERT INTO device_registry (
                device_id,
                device_model,
                expected_port,
                status,
                first_seen_at,
                last_seen_at,
                last_heartbeat_at,
                last_event_at,
                last_source_ip,
                last_listener_port,
                learning_mode,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, 'online', %s, %s, %s, %s, %s, %s, true, now(), now()
            )
            ON CONFLICT (device_id) DO UPDATE
            SET
                device_model = COALESCE(EXCLUDED.device_model, device_registry.device_model),
                expected_port = COALESCE(device_registry.expected_port, EXCLUDED.expected_port),
                status = 'online',
                last_seen_at = EXCLUDED.last_seen_at,
                last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                last_event_at = COALESCE(
                    GREATEST(device_registry.last_event_at, EXCLUDED.last_event_at),
                    EXCLUDED.last_event_at
                ),
                last_source_ip = EXCLUDED.last_source_ip,
                last_listener_port = EXCLUDED.last_listener_port,
                updated_at = now()
            """,
            (
                device_id,
                device_model,
                listener_port,
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                source_ip,
                listener_port,
            ),
        )
        cur.execute(
            """
            INSERT INTO device_status (
                device_id,
                last_seen_at,
                last_heartbeat_at,
                last_event_at,
                last_event_kind,
                status,
                heartbeat_interval_seconds,
                stale_since,
                offline_since,
                last_source_ip,
                last_listener_port,
                updated_at
            )
            VALUES (%s, %s, %s, %s, 'heartbeat_connect', 'online', %s, NULL, NULL, %s, %s, now())
            ON CONFLICT (device_id) DO UPDATE
            SET
                last_seen_at = EXCLUDED.last_seen_at,
                last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                last_event_at = EXCLUDED.last_event_at,
                last_event_kind = EXCLUDED.last_event_kind,
                status = 'online',
                heartbeat_interval_seconds = COALESCE(EXCLUDED.heartbeat_interval_seconds, device_status.heartbeat_interval_seconds),
                stale_since = NULL,
                offline_since = NULL,
                last_source_ip = EXCLUDED.last_source_ip,
                last_listener_port = EXCLUDED.last_listener_port,
                updated_at = now()
            """,
            (
                device_id,
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                heartbeat_interval,
                source_ip,
                listener_port,
            ),
        )

    def _touch_device_for_business_event(
        self,
        cur: psycopg.Cursor[Any],
        *,
        device_id: str,
        event_kind: str,
        source_ip: str | None,
        listener_port: int | None,
        event_occurred_at: datetime,
    ) -> None:
        cur.execute(
            """
            UPDATE device_registry
            SET
                last_seen_at = GREATEST(last_seen_at, %s),
                last_event_at = GREATEST(COALESCE(last_event_at, %s), %s),
                last_source_ip = COALESCE(%s, last_source_ip),
                last_listener_port = COALESCE(%s, last_listener_port),
                updated_at = now()
            WHERE device_id = %s
            """,
            (
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                source_ip,
                listener_port,
                device_id,
            ),
        )
        cur.execute(
            """
            UPDATE device_status
            SET
                last_seen_at = GREATEST(COALESCE(last_seen_at, %s), %s),
                last_event_at = GREATEST(COALESCE(last_event_at, %s), %s),
                last_event_kind = %s,
                last_source_ip = COALESCE(%s, last_source_ip),
                last_listener_port = COALESCE(%s, last_listener_port),
                updated_at = now()
            WHERE device_id = %s
            """,
            (
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                event_occurred_at,
                event_kind,
                source_ip,
                listener_port,
                device_id,
            ),
        )

    def _insert_quarantine(
        self,
        cur: psycopg.Cursor[Any],
        *,
        raw_request_id: int,
        raw_received_at_utc: datetime,
        source_ip: str | None,
        listener_port: int | None,
        payload_hash: str | None,
        reason: str,
        candidate_device_id: str | None,
        event_kind: str,
        body: Any,
    ) -> None:
        cur.execute(
            """
            INSERT INTO event_quarantine (
                raw_request_id,
                raw_received_at_utc,
                source_ip,
                listener_port,
                payload_hash,
                reason,
                candidate_device_id,
                event_kind,
                body_jsonb
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                raw_request_id,
                raw_received_at_utc,
                source_ip,
                listener_port,
                payload_hash,
                reason,
                candidate_device_id,
                event_kind,
                Jsonb(body),
            ),
        )

    def _enqueue_outbox(
        self,
        cur: psycopg.Cursor[Any],
        normalized_event_id: int,
        payload: dict[str, Any],
    ) -> None:
        cur.execute(
            """
            INSERT INTO outbox_sync (
                normalized_event_id,
                event_occurred_at_utc,
                target,
                status,
                payload_jsonb
            )
            VALUES (%s, %s, 'odoo', 'pending', %s)
            """,
            (
                normalized_event_id,
                payload["event_occurred_at_utc"],
                Jsonb(
                    {
                        "normalized_event_id": normalized_event_id,
                        "event_kind": payload["event_kind"],
                        "device_id_resolved": payload["device_id_resolved"],
                        "user_id_on_device": payload["user_id_on_device"],
                        "card_name": payload["card_name"],
                        "door_name": payload["door_name"],
                        "direction": payload["direction"],
                        "granted": payload["granted"],
                        "error_code": payload["error_code"],
                        "method_code": payload["method_code"],
                        "reader_id": payload["reader_id"],
                        "card_no": payload["card_no"],
                        "user_type_code": payload["user_type_code"],
                        "door_index": payload["door_index"],
                        "block_id": payload["block_id"],
                        "stream_index": payload["stream_index"],
                        "event_occurred_at_utc": payload["event_occurred_at_utc"].astimezone(timezone.utc).isoformat(),
                    }
                ),
            ),
        )

    def record_processing_error(
        self,
        *,
        stage: str,
        error_message: str,
        payload: dict[str, Any] | None,
        ingest_id: str | None = None,
        raw_request_id: int | None = None,
        raw_received_at_utc: datetime | None = None,
        retryable: bool = True,
    ) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO processing_error (
                        stage,
                        ingest_id,
                        raw_request_id,
                        raw_received_at_utc,
                        error_message,
                        payload_jsonb,
                        retryable
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        stage,
                        ingest_id,
                        raw_request_id,
                        raw_received_at_utc,
                        error_message,
                        Jsonb(payload),
                        retryable,
                    ),
                )

    def reprocess_quarantine(self) -> tuple[int, int]:
        """Reprocess quarantine events that qualify for normalization.

        Returns (reprocessed_count, skipped_count).
        AccessControl events with a usable UserID are valid even without a
        resolved device_id, so only those quarantine rows are moved into
        normalized_event.
        """
        reprocessed = 0
        skipped = 0

        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT q.id, q.raw_request_id, q.raw_received_at_utc,
                           q.source_ip, q.listener_port, q.event_kind,
                           q.body_jsonb, q.reason
                    FROM event_quarantine q
                    WHERE q.event_kind = 'access_control'
                      AND q.body_jsonb -> 'Data' ->> 'UserID' IS NOT NULL
                      AND btrim(q.body_jsonb -> 'Data' ->> 'UserID') != ''
                    ORDER BY q.id
                    """
                )
                rows = cur.fetchall()

                for row in rows:
                    q_id, raw_request_id, raw_received_at_utc = row[0], row[1], row[2]
                    source_ip, listener_port = row[3], row[4]
                    event_kind, body, reason = row[5], row[6], row[7]

                    body_dict = body if isinstance(body, dict) else None
                    event_occurred_at = (
                        epoch_to_datetime(select_event_epoch(body_dict))
                        or raw_received_at_utc
                    )
                    self._ensure_partition(cur, "normalized_event", event_occurred_at)

                    event_proxy = {
                        "source_ip": str(source_ip) if source_ip else None,
                        "listener_port": listener_port,
                        "body": body,
                        "event_kind_detected": event_kind,
                    }

                    normalized_payload = self._build_normalized_payload(
                        raw_request_id=raw_request_id,
                        raw_received_at_utc=raw_received_at_utc,
                        event=event_proxy,
                        body=body_dict,
                        event_kind=event_kind,
                        event_occurred_at=event_occurred_at,
                        resolved_device_id=None,
                        identity_resolution=reason or "reprocessed_from_quarantine",
                    )
                    self._insert_normalized_event(cur, normalized_payload)
                    cur.execute(
                        "DELETE FROM event_quarantine WHERE id = %s", (q_id,)
                    )
                    reprocessed += 1

        return reprocessed, skipped
