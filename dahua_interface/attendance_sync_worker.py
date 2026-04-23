#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
import socket
import time
import traceback
import xmlrpc.client
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from biometric_common import ensure_directory


DEFAULT_LOG_PATH = Path("/var/log/biometric-ingest/attendance-sync.log")
DEFAULT_SOURCE_MODE = "biometric_v1"
DEFAULT_INFERENCE_MODE = "biometric_v1_raw_toggle"


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def odoo_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")


def parse_odoo_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def parse_local_time(raw: str, default: str) -> dt_time:
    candidate = raw or default
    return datetime.strptime(candidate, "%H:%M").time()


def choose_zone(name: str, fallback: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001
        return ZoneInfo(fallback)


def local_end_of_day_utc(target_date: date, tz_name: str) -> datetime:
    zone = choose_zone(tz_name, "America/Mexico_City")
    local_dt = datetime.combine(target_date, dt_time(23, 59, 59), tzinfo=zone)
    return local_dt.astimezone(UTC)


@dataclass(slots=True)
class SyncSettings:
    biometric_db_url: str
    odoo_url: str
    odoo_db: str
    odoo_login: str
    odoo_password: str
    log_path: Path
    batch_size: int
    poll_seconds: int
    default_timezone: str
    source_mode_label: str
    inference_mode: str

    @classmethod
    def from_env(cls) -> "SyncSettings":
        biometric_db_url = os.getenv("ATTENDANCE_SYNC_BIOMETRIC_DATABASE_URL") or os.getenv("BIOMETRIC_DATABASE_URL")
        if not biometric_db_url:
            raise RuntimeError("ATTENDANCE_SYNC_BIOMETRIC_DATABASE_URL or BIOMETRIC_DATABASE_URL is required")

        odoo_url = os.getenv("ATTENDANCE_SYNC_ODOO_URL", "http://127.0.0.1:8069").rstrip("/")
        odoo_db = os.getenv("ATTENDANCE_SYNC_ODOO_DB", "devlyn_com")
        odoo_login = os.getenv("ATTENDANCE_SYNC_ODOO_LOGIN", "").strip()
        odoo_password = os.getenv("ATTENDANCE_SYNC_ODOO_PASSWORD", "").strip()
        if not odoo_login or not odoo_password:
            raise RuntimeError("ATTENDANCE_SYNC_ODOO_LOGIN and ATTENDANCE_SYNC_ODOO_PASSWORD are required")

        return cls(
            biometric_db_url=biometric_db_url,
            odoo_url=odoo_url,
            odoo_db=odoo_db,
            odoo_login=odoo_login,
            odoo_password=odoo_password,
            log_path=Path(os.getenv("ATTENDANCE_SYNC_LOG", str(DEFAULT_LOG_PATH))),
            batch_size=max(1, int(os.getenv("ATTENDANCE_SYNC_BATCH_SIZE", "100"))),
            poll_seconds=max(5, int(os.getenv("ATTENDANCE_SYNC_POLL_SECONDS", "60"))),
            default_timezone=os.getenv("ATTENDANCE_SYNC_DEFAULT_TIMEZONE", "America/Mexico_City"),
            source_mode_label=os.getenv("ATTENDANCE_SYNC_SOURCE_MODE_LABEL", DEFAULT_SOURCE_MODE),
            inference_mode=os.getenv("ATTENDANCE_SYNC_INFERENCE_MODE", DEFAULT_INFERENCE_MODE),
        )


def configure_logger(path: Path) -> logging.Logger:
    ensure_directory(path.parent)
    logger = logging.getLogger("attendance_sync_worker")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(stream)
    return logger


class OdooClient:
    def __init__(self, settings: SyncSettings):
        common_url = f"{settings.odoo_url}/xmlrpc/2/common"
        object_url = f"{settings.odoo_url}/xmlrpc/2/object"
        self.settings = settings
        self.common = xmlrpc.client.ServerProxy(common_url, allow_none=True)
        self.object = xmlrpc.client.ServerProxy(object_url, allow_none=True)
        self.uid = self.common.authenticate(
            settings.odoo_db,
            settings.odoo_login,
            settings.odoo_password,
            {},
        )
        if not self.uid:
            raise RuntimeError("Could not authenticate against Odoo XML-RPC")

    def execute(self, model: str, method: str, *args: Any, **kwargs: Any) -> Any:
        return self.object.execute_kw(
            self.settings.odoo_db,
            self.uid,
            self.settings.odoo_password,
            model,
            method,
            list(args),
            kwargs,
        )

    def search_read(
        self,
        model: str,
        domain: list[Any],
        fields: list[str],
        *,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"fields": fields}
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute(model, "search_read", domain, **kwargs)

    def create(self, model: str, vals: dict[str, Any], *, context: dict[str, Any] | None = None) -> int:
        kwargs: dict[str, Any] = {}
        if context:
            kwargs["context"] = context
        return self.execute(model, "create", vals, **kwargs)

    def write(
        self,
        model: str,
        record_ids: list[int],
        vals: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> bool:
        kwargs: dict[str, Any] = {}
        if context:
            kwargs["context"] = context
        return self.execute(model, "write", record_ids, vals, **kwargs)

    def search_count(self, model: str, domain: list[Any]) -> int:
        return self.execute(model, "search_count", domain)


class AttendanceSyncWorker:
    def __init__(self, settings: SyncSettings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.hostname = socket.gethostname()
        self.sleep_seconds = settings.poll_seconds
        self.db = psycopg.connect(settings.biometric_db_url, row_factory=dict_row)
        self.db.autocommit = False
        self.odoo = OdooClient(settings)

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:  # noqa: BLE001
            self.logger.exception("Could not close biometric database connection")

    def run_forever(self) -> int:
        while True:
            try:
                self.run_cycle()
                time.sleep(self.sleep_seconds)
            except KeyboardInterrupt:
                self.logger.info("Attendance sync worker interrupted")
                return 130
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Attendance sync cycle failed: %s", exc)
                time.sleep(max(self.sleep_seconds, 5))

    def run_cycle(self) -> None:
        config = self._get_config()
        self.sleep_seconds = max(5, int(config.get("sync_interval_seconds") or self.settings.poll_seconds))
        cursor = self._get_cursor()
        counts = {
            "processed_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "error_count": 0,
        }
        last_processed_id = cursor.get("last_normalized_event_id") or 0
        run_id: int | None = None

        try:
            rows = self._fetch_normalized_events(last_processed_id, self.settings.batch_size)
            if not rows:
                self.logger.debug("No pending normalized events for attendance sync.")
            else:
                run_id = self._create_run("sync", last_processed_id)
                employee_map = self._fetch_employee_map(rows)
                existing_map = self._fetch_existing_event_map(rows)
                for row in rows:
                    normalized_event_id = int(row["id"])
                    existing = existing_map.get(normalized_event_id)
                    if existing and existing["sync_status"] not in {"pending", "error"}:
                        counts["skipped_count"] += 1
                        last_processed_id = normalized_event_id
                        self._update_cursor(cursor["id"], normalized_event_id, row["event_occurred_at_utc"])
                        continue

                    try:
                        user_key = str(row["user_id_on_device"]).strip() if row.get("user_id_on_device") else ""
                        outcome = self._process_event(row, employee_map.get(user_key), existing, config)
                        counts["processed_count"] += 1
                        if outcome in {"check_in_created", "employee_not_found", "denied_ignored"}:
                            counts["created_count"] += 1
                        elif outcome in {"check_out_written", "duplicate_ignored", "after_close_review"}:
                            counts["updated_count"] += 1
                        else:
                            counts["skipped_count"] += 1
                    except Exception as exc:  # noqa: BLE001
                        counts["error_count"] += 1
                        self._upsert_event_record(
                            row=row,
                            employee=None,
                            existing_event=existing,
                            config=config,
                            sync_status="error",
                            attendance_action="error",
                            attendance_id=False,
                            message=f"{type(exc).__name__}: {exc}",
                            dedupe_reference_event_id=False,
                            auto_closed=False,
                            auto_close_reason=False,
                        )
                        self.logger.exception("Failed processing normalized_event_id=%s", normalized_event_id)

                    last_processed_id = normalized_event_id
                    self._update_cursor(cursor["id"], normalized_event_id, row["event_occurred_at_utc"])

                self._finalize_run(run_id, "success", counts, f"Processed {len(rows)} normalized events.", last_processed_id)
                self.logger.info(
                    "Sync run completed: processed=%s created=%s updated=%s skipped=%s errors=%s last_id=%s",
                    counts["processed_count"],
                    counts["created_count"],
                    counts["updated_count"],
                    counts["skipped_count"],
                    counts["error_count"],
                    last_processed_id,
                )
        except Exception as exc:  # noqa: BLE001
            message = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            if run_id is not None:
                self._finalize_run(run_id, "failed", counts, message, last_processed_id)
            raise

        self._run_close_if_due(config)
        self._run_reconcile_if_due(config)

    def _fetch_normalized_events(self, last_id: int, batch_size: int) -> list[dict[str, Any]]:
        query = """
            SELECT
                id,
                raw_request_id,
                event_occurred_at_utc,
                event_kind,
                device_id_resolved,
                source_ip::text AS source_ip,
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
                identity_resolution
            FROM normalized_event
            WHERE id > %s
              AND event_kind = 'access_control'
            ORDER BY id
            LIMIT %s
        """
        with self.db.transaction():
            with self.db.cursor() as cur:
                cur.execute(query, (last_id, batch_size))
                rows = cur.fetchall()
        return rows

    def _fetch_employee_map(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
        employee_numbers = sorted({str(row["user_id_on_device"]).strip() for row in rows if row.get("user_id_on_device")})
        if not employee_numbers:
            return {}
        employees = self.odoo.search_read(
            "hr.employee",
            [["employee_number", "in", employee_numbers], ["active", "=", True]],
            ["id", "name", "employee_number"],
        )
        mapping: dict[str, dict[str, Any] | None] = {number: None for number in employee_numbers}
        grouped: dict[str, list[dict[str, Any]]] = {}
        for employee in employees:
            employee_number = str(employee["employee_number"]).strip()
            grouped.setdefault(employee_number, []).append(employee)
        for number in employee_numbers:
            matches = grouped.get(number, [])
            mapping[number] = matches[0] if len(matches) == 1 else None
        return mapping

    def _fetch_existing_event_map(self, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        ids = [int(row["id"]) for row in rows]
        if not ids:
            return {}
        existing_rows = self.odoo.search_read(
            "hr.biometric.event",
            [["normalized_event_id", "in", ids]],
            ["id", "normalized_event_id", "sync_status"],
        )
        return {int(row["normalized_event_id"]): row for row in existing_rows}

    def _get_config(self) -> dict[str, Any]:
        rows = self.odoo.search_read(
            "hr.biometric.sync.config",
            [],
            [
                "id",
                "timezone_name",
                "sync_interval_seconds",
                "debounce_seconds",
                "close_time_local",
                "reconcile_time_local",
                "source_mode_label",
                "auto_close_enabled",
                "reconcile_enabled",
                "accept_unresolved_device",
                "last_close_run_date",
                "last_reconcile_run_date",
            ],
            limit=1,
        )
        if rows:
            return rows[0]
        return {
            "id": self.odoo.create(
                "hr.biometric.sync.config",
                {
                    "name": "Default",
                    "timezone_name": self.settings.default_timezone,
                    "sync_interval_seconds": self.settings.poll_seconds,
                    "debounce_seconds": 90,
                    "close_time_local": "23:59",
                    "reconcile_time_local": "00:15",
                    "source_mode_label": self.settings.source_mode_label,
                    "auto_close_enabled": True,
                    "reconcile_enabled": True,
                    "accept_unresolved_device": True,
                },
            )
        } | {
            "timezone_name": self.settings.default_timezone,
            "sync_interval_seconds": self.settings.poll_seconds,
            "debounce_seconds": 90,
            "close_time_local": "23:59",
            "reconcile_time_local": "00:15",
            "source_mode_label": self.settings.source_mode_label,
            "auto_close_enabled": True,
            "reconcile_enabled": True,
            "accept_unresolved_device": True,
            "last_close_run_date": False,
            "last_reconcile_run_date": False,
        }

    def _get_cursor(self) -> dict[str, Any]:
        rows = self.odoo.search_read(
            "hr.biometric.sync.cursor",
            [["name", "=", "main"]],
            ["id", "name", "last_normalized_event_id", "last_event_occurred_at_utc", "last_success_at"],
            limit=1,
        )
        if rows:
            return rows[0]
        cursor_id = self.odoo.create(
            "hr.biometric.sync.cursor",
            {
                "name": "main",
                "last_normalized_event_id": 0,
            },
        )
        return {
            "id": cursor_id,
            "name": "main",
            "last_normalized_event_id": 0,
            "last_event_occurred_at_utc": False,
            "last_success_at": False,
        }

    def _create_run(self, run_type: str, last_normalized_event_id: int) -> int:
        now = utc_now()
        return self.odoo.create(
            "hr.biometric.sync.run",
            {
                "name": f"{run_type.upper()} {now.strftime('%Y-%m-%d %H:%M:%S')}",
                "run_type": run_type,
                "status": "running",
                "started_at": odoo_datetime(now),
                "last_normalized_event_id": last_normalized_event_id,
                "message": f"Started on {self.hostname}",
            },
        )

    def _finalize_run(
        self,
        run_id: int,
        status: str,
        counts: dict[str, int],
        message: str,
        last_normalized_event_id: int,
    ) -> None:
        vals = {
            "status": status,
            "finished_at": odoo_datetime(utc_now()),
            "last_normalized_event_id": last_normalized_event_id,
            "processed_count": counts["processed_count"],
            "created_count": counts["created_count"],
            "updated_count": counts["updated_count"],
            "skipped_count": counts["skipped_count"],
            "error_count": counts["error_count"],
            "message": message,
        }
        self.odoo.write("hr.biometric.sync.run", [run_id], vals)

    def _update_cursor(self, cursor_id: int, last_normalized_event_id: int, event_occurred_at_utc: datetime) -> None:
        self.odoo.write(
            "hr.biometric.sync.cursor",
            [cursor_id],
            {
                "last_normalized_event_id": last_normalized_event_id,
                "last_event_occurred_at_utc": odoo_datetime(event_occurred_at_utc),
                "last_success_at": odoo_datetime(utc_now()),
            },
        )

    def _process_event(
        self,
        row: dict[str, Any],
        employee: dict[str, Any] | None,
        existing_event: dict[str, Any] | None,
        config: dict[str, Any],
    ) -> str:
        event_local = self._to_local(row["event_occurred_at_utc"], config["timezone_name"])
        current_local = utc_now().astimezone(choose_zone(config["timezone_name"], self.settings.default_timezone))

        if not row.get("user_id_on_device"):
            return self._upsert_event_record(
                row=row,
                employee=None,
                existing_event=existing_event,
                config=config,
                sync_status="error",
                attendance_action="error",
                attendance_id=False,
                message="UserID is empty for access_control.",
                dedupe_reference_event_id=False,
                auto_closed=False,
                auto_close_reason=False,
            )

        if employee is None:
            return self._upsert_event_record(
                row=row,
                employee=None,
                existing_event=existing_event,
                config=config,
                sync_status="employee_not_found",
                attendance_action="employee_not_found",
                attendance_id=False,
                message="No active employee matched by employee_number.",
                dedupe_reference_event_id=False,
                auto_closed=False,
                auto_close_reason=False,
            )

        if row.get("granted") is not True:
            return self._upsert_event_record(
                row=row,
                employee=employee,
                existing_event=existing_event,
                config=config,
                sync_status="denied_ignored",
                attendance_action="denied_ignored",
                attendance_id=False,
                message="Access control event was not granted.",
                dedupe_reference_event_id=False,
                auto_closed=False,
                auto_close_reason=False,
            )

        last_close_run_date = self._parse_odoo_date(config.get("last_close_run_date"))
        if last_close_run_date and event_local.date() <= last_close_run_date and event_local.date() < current_local.date():
            return self._upsert_event_record(
                row=row,
                employee=employee,
                existing_event=existing_event,
                config=config,
                sync_status="after_close_review",
                attendance_action="after_close_review",
                attendance_id=False,
                message="Late event detected after end-of-day close.",
                dedupe_reference_event_id=False,
                auto_closed=False,
                auto_close_reason=False,
            )

        previous_event = self._find_latest_accepted_event(employee["id"])
        if previous_event:
            previous_dt = parse_odoo_datetime(previous_event.get("event_occurred_at_utc"))
            if previous_dt is not None:
                gap_seconds = (row["event_occurred_at_utc"] - previous_dt).total_seconds()
                if gap_seconds <= int(config["debounce_seconds"]):
                    return self._upsert_event_record(
                        row=row,
                        employee=employee,
                        existing_event=existing_event,
                        config=config,
                        sync_status="duplicate_ignored",
                        attendance_action="duplicate_ignored",
                        attendance_id=previous_event.get("attendance_id") and previous_event["attendance_id"][0] or False,
                        message=f"Duplicate within debounce window ({int(gap_seconds)}s).",
                        dedupe_reference_event_id=previous_event["id"],
                        auto_closed=False,
                        auto_close_reason=False,
                    )

        event_id, _ = self._upsert_event_record(
            row=row,
            employee=employee,
            existing_event=existing_event,
            config=config,
            sync_status="pending",
            attendance_action=False,
            attendance_id=False,
            message="Pending attendance decision.",
            dedupe_reference_event_id=False,
            auto_closed=False,
            auto_close_reason=False,
            return_record_id=True,
        )

        open_attendance = self._find_open_attendance(employee["id"])
        if open_attendance:
            open_check_in = parse_odoo_datetime(open_attendance.get("check_in"))
            if open_check_in is not None and self._to_local(open_check_in, config["timezone_name"]).date() < event_local.date():
                close_dt = local_end_of_day_utc(
                    self._to_local(open_check_in, config["timezone_name"]).date(),
                    config["timezone_name"],
                )
                self._write_attendance(
                    open_attendance["id"],
                    {
                        "check_out": odoo_datetime(close_dt),
                        "biometric_auto_closed": True,
                        "biometric_auto_close_reason": "auto_close_before_new_day_v1",
                    },
                )
                checkin_event = open_attendance.get("biometric_checkin_event_id")
                if checkin_event:
                    self.odoo.write(
                        "hr.biometric.event",
                        [checkin_event[0]],
                        {
                            "attendance_auto_closed": True,
                            "auto_close_reason": "auto_close_before_new_day_v1",
                        },
                    )
                open_attendance = None

        if open_attendance:
            self._write_attendance(
                open_attendance["id"],
                {
                    "check_out": odoo_datetime(row["event_occurred_at_utc"]),
                    "biometric_checkout_event_id": event_id,
                    "biometric_source": config["source_mode_label"],
                    "biometric_inference_mode": self.settings.inference_mode,
                },
            )
            self.odoo.write(
                "hr.biometric.event",
                [event_id],
                {
                    "sync_status": "check_out_written",
                    "attendance_action": "check_out_written",
                    "attendance_id": open_attendance["id"],
                    "message": "Open attendance closed by raw toggle v1.",
                },
            )
            return "check_out_written"

        attendance_id = self.odoo.create(
            "hr.attendance",
            {
                "employee_id": employee["id"],
                "check_in": odoo_datetime(row["event_occurred_at_utc"]),
                "biometric_source": config["source_mode_label"],
                "biometric_inference_mode": self.settings.inference_mode,
                "biometric_checkin_event_id": event_id,
            },
        )
        self.odoo.write(
            "hr.biometric.event",
            [event_id],
            {
                "sync_status": "check_in_created",
                "attendance_action": "check_in_created",
                "attendance_id": attendance_id,
                "message": "Attendance check-in created by raw toggle v1.",
            },
        )
        return "check_in_created"

    def _upsert_event_record(
        self,
        *,
        row: dict[str, Any],
        employee: dict[str, Any] | None,
        existing_event: dict[str, Any] | None,
        config: dict[str, Any],
        sync_status: str,
        attendance_action: str | bool,
        attendance_id: int | bool,
        message: str,
        dedupe_reference_event_id: int | bool,
        auto_closed: bool,
        auto_close_reason: str | bool,
        return_record_id: bool = False,
    ) -> Any:
        event_local = self._to_local(row["event_occurred_at_utc"], config["timezone_name"])
        vals = {
            "name": f"{row['user_id_on_device'] or 'unknown'} - {event_local.strftime('%Y-%m-%d %H:%M:%S')}",
            "normalized_event_id": int(row["id"]),
            "source_raw_request_id": row.get("raw_request_id"),
            "event_kind": row.get("event_kind") or "access_control",
            "event_occurred_at_utc": odoo_datetime(row["event_occurred_at_utc"]),
            "event_local_date": event_local.date().isoformat(),
            "event_local_display": event_local.strftime("%Y-%m-%d %I:%M:%S %p"),
            "user_id_on_device": row.get("user_id_on_device"),
            "card_name": row.get("card_name"),
            "employee_id": employee["id"] if employee else False,
            "device_id_resolved": row.get("device_id_resolved") or False,
            "identity_resolution": row.get("identity_resolution") or False,
            "source_ip": row.get("source_ip") or False,
            "door_name": row.get("door_name") or False,
            "reader_id": row.get("reader_id") or False,
            "direction_raw": self._direction_raw(row.get("direction")),
            "granted_state": self._granted_state(row.get("granted")),
            "sync_status": sync_status,
            "attendance_action": attendance_action or False,
            "attendance_id": attendance_id or False,
            "dedupe_reference_event_id": dedupe_reference_event_id or False,
            "inference_mode": self.settings.inference_mode,
            "attendance_auto_closed": auto_closed,
            "auto_close_reason": auto_close_reason or False,
            "message": message,
            "payload_json": {
                "normalized_event_id": int(row["id"]),
                "event_occurred_at_utc": row["event_occurred_at_utc"].astimezone(UTC).isoformat(),
                "device_id_resolved": row.get("device_id_resolved"),
                "user_id_on_device": row.get("user_id_on_device"),
                "card_name": row.get("card_name"),
                "door_name": row.get("door_name"),
                "direction": row.get("direction"),
                "granted": row.get("granted"),
                "error_code": row.get("error_code"),
                "method_code": row.get("method_code"),
                "reader_id": row.get("reader_id"),
                "card_no": row.get("card_no"),
                "user_type_code": row.get("user_type_code"),
                "door_index": row.get("door_index"),
                "block_id": row.get("block_id"),
                "stream_index": row.get("stream_index"),
                "identity_resolution": row.get("identity_resolution"),
                "source_ip": row.get("source_ip"),
                "body_jsonb": row.get("body_jsonb") or {},
            },
        }
        if existing_event:
            self.odoo.write("hr.biometric.event", [existing_event["id"]], vals)
            if return_record_id:
                return existing_event["id"], vals
            return sync_status
        event_id = self.odoo.create("hr.biometric.event", vals)
        if return_record_id:
            return event_id, vals
        return sync_status

    def _find_latest_accepted_event(self, employee_id: int) -> dict[str, Any] | None:
        rows = self.odoo.search_read(
            "hr.biometric.event",
            [
                ["employee_id", "=", employee_id],
                ["sync_status", "in", ["check_in_created", "check_out_written"]],
            ],
            ["id", "event_occurred_at_utc", "attendance_id"],
            limit=1,
            order="event_occurred_at_utc desc,id desc",
        )
        return rows[0] if rows else None

    def _find_open_attendance(self, employee_id: int) -> dict[str, Any] | None:
        rows = self.odoo.search_read(
            "hr.attendance",
            [["employee_id", "=", employee_id], ["check_out", "=", False]],
            ["id", "check_in", "biometric_checkin_event_id"],
            limit=1,
            order="check_in desc,id desc",
        )
        return rows[0] if rows else None

    def _write_attendance(
        self,
        attendance_id: int,
        vals: dict[str, Any],
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.odoo.write("hr.attendance", [attendance_id], vals, context=context)

    def _run_close_if_due(self, config: dict[str, Any]) -> None:
        if not config.get("auto_close_enabled"):
            return
        now_local = utc_now().astimezone(choose_zone(config["timezone_name"], self.settings.default_timezone))
        run_date = now_local.date()
        last_close_run_date = self._parse_odoo_date(config.get("last_close_run_date"))
        if last_close_run_date == run_date:
            return
        if now_local.time() < parse_local_time(config.get("close_time_local") or "23:59", "23:59"):
            return

        run_id = self._create_run("close", 0)
        counts = {"processed_count": 0, "created_count": 0, "updated_count": 0, "skipped_count": 0, "error_count": 0}
        try:
            attendances = self.odoo.search_read(
                "hr.attendance",
                [["check_out", "=", False], ["biometric_source", "=", config["source_mode_label"]]],
                ["id", "check_in", "biometric_checkin_event_id"],
                limit=1000,
                order="check_in asc,id asc",
            )
            for attendance in attendances:
                check_in_dt = parse_odoo_datetime(attendance.get("check_in"))
                if check_in_dt is None:
                    counts["skipped_count"] += 1
                    continue
                close_dt = local_end_of_day_utc(
                    self._to_local(check_in_dt, config["timezone_name"]).date(),
                    config["timezone_name"],
                )
                self._write_attendance(
                    attendance["id"],
                    {
                        "check_out": odoo_datetime(close_dt),
                        "biometric_auto_closed": True,
                        "biometric_auto_close_reason": "auto_close_eod_v1",
                    },
                )
                checkin_event = attendance.get("biometric_checkin_event_id")
                if checkin_event:
                    self.odoo.write(
                        "hr.biometric.event",
                        [checkin_event[0]],
                        {
                            "attendance_auto_closed": True,
                            "auto_close_reason": "auto_close_eod_v1",
                        },
                    )
                counts["processed_count"] += 1
                counts["updated_count"] += 1

            self.odoo.write(
                "hr.biometric.sync.config",
                [config["id"]],
                {"last_close_run_date": run_date.isoformat()},
            )
            self._finalize_run(run_id, "success", counts, f"Closed {counts['updated_count']} open biometric attendances.", 0)
            self.logger.info("Daily close run completed: closed=%s", counts["updated_count"])
        except Exception as exc:  # noqa: BLE001
            counts["error_count"] += 1
            self._finalize_run(run_id, "failed", counts, str(exc), 0)
            raise

    def _run_reconcile_if_due(self, config: dict[str, Any]) -> None:
        if not config.get("reconcile_enabled"):
            return
        now_local = utc_now().astimezone(choose_zone(config["timezone_name"], self.settings.default_timezone))
        run_date = now_local.date()
        last_reconcile_run_date = self._parse_odoo_date(config.get("last_reconcile_run_date"))
        if last_reconcile_run_date == run_date:
            return
        if now_local.time() < parse_local_time(config.get("reconcile_time_local") or "00:15", "00:15"):
            return

        run_id = self._create_run("reconcile", 0)
        counts = {"processed_count": 0, "created_count": 0, "updated_count": 0, "skipped_count": 0, "error_count": 0}
        previous_day = run_date - timedelta(days=1)
        try:
            review_count = self.odoo.search_count(
                "hr.biometric.event",
                [["event_local_date", "=", previous_day.isoformat()], ["sync_status", "=", "after_close_review"]],
            )
            counts["processed_count"] = review_count
            counts["skipped_count"] = review_count
            self.odoo.write(
                "hr.biometric.sync.config",
                [config["id"]],
                {"last_reconcile_run_date": run_date.isoformat()},
            )
            self._finalize_run(
                run_id,
                "success",
                counts,
                f"Found {review_count} after_close_review events for {previous_day.isoformat()}.",
                0,
            )
            self.logger.info(
                "Reconcile run completed: previous_day=%s after_close_review=%s",
                previous_day.isoformat(),
                review_count,
            )
        except Exception as exc:  # noqa: BLE001
            counts["error_count"] += 1
            self._finalize_run(run_id, "failed", counts, str(exc), 0)
            raise

    def _parse_odoo_date(self, raw: Any) -> date | None:
        if not raw:
            return None
        if isinstance(raw, date):
            return raw
        return datetime.strptime(raw, "%Y-%m-%d").date()

    def _to_local(self, dt_utc: datetime, tz_name: str) -> datetime:
        zone = choose_zone(tz_name, self.settings.default_timezone)
        return dt_utc.astimezone(zone)

    def _direction_raw(self, raw: str | None) -> str:
        if raw in {"entry", "exit", "unknown"}:
            return raw
        return "unknown"

    def _granted_state(self, raw: bool | None) -> str:
        if raw is True:
            return "granted"
        if raw is False:
            return "denied"
        return "unknown"


def main() -> int:
    settings = SyncSettings.from_env()
    logger = configure_logger(settings.log_path)
    worker = AttendanceSyncWorker(settings, logger)
    try:
        return worker.run_forever()
    finally:
        worker.close()


if __name__ == "__main__":
    raise SystemExit(main())
