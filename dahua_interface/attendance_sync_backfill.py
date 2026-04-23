#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as dt_time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from attendance_sync_worker import (
    AttendanceSyncWorker,
    SyncSettings,
    choose_zone,
    configure_logger,
    local_end_of_day_utc,
    odoo_datetime,
    parse_odoo_datetime,
)


ACCEPTED_SYNC_STATUSES = {"check_in_created", "check_out_written"}
RANGE_CONFLICT_STATUS = "conflict_preserved"
EXISTING_SYNCED_STATUS = "already_synced"


@dataclass(slots=True)
class BackfillArgs:
    mode: str
    id_from: int
    id_to: int
    report_dir: Path
    odoo_db: str
    biometric_db: str
    cursor_name: str
    batch_size: int


@dataclass(slots=True)
class SimAcceptedEvent:
    event_id: int
    occurred_at_utc: datetime
    attendance_id: int | None


@dataclass(slots=True)
class PendingAttendanceState:
    local_date: date
    check_in_utc: datetime
    attendance_id: int | None = None
    checkin_event_id: int | None = None
    checkin_row: dict[str, Any] | None = None


class AttendanceSyncBackfill:
    def __init__(self, args: BackfillArgs):
        self.args = args
        self.args.report_dir.mkdir(parents=True, exist_ok=True)
        self.settings = SyncSettings.from_env()
        biometric_db_url = self._with_database_name(self.settings.biometric_db_url, args.biometric_db)
        self.settings = SyncSettings(
            biometric_db_url=biometric_db_url,
            odoo_url=self.settings.odoo_url,
            odoo_db=args.odoo_db or self.settings.odoo_db,
            odoo_login=self.settings.odoo_login,
            odoo_password=self.settings.odoo_password,
            log_path=args.report_dir / "attendance-backfill.log",
            batch_size=args.batch_size or self.settings.batch_size,
            poll_seconds=self.settings.poll_seconds,
            default_timezone=self.settings.default_timezone,
            source_mode_label=self.settings.source_mode_label,
            inference_mode=self.settings.inference_mode,
        )
        self.logger = configure_logger(self.settings.log_path)
        self.worker = AttendanceSyncWorker(self.settings, self.logger)
        self.config = self.worker._get_config()
        self.zone = choose_zone(self.config["timezone_name"], self.settings.default_timezone)
        self.range_rows: list[dict[str, Any]] = []
        self.employee_map: dict[str, dict[str, Any] | None] = {}
        self.existing_event_map: dict[int, dict[str, Any]] = {}
        self.preexisting_conflicts: dict[tuple[int, date], list[dict[str, Any]]] = {}
        self.cursor_snapshot: dict[str, Any] = {}

    @staticmethod
    def _with_database_name(database_url: str, database_name: str) -> str:
        if not database_name:
            return database_url
        parts = urlsplit(database_url)
        if not parts.scheme or not parts.netloc:
            return database_url
        return urlunsplit((parts.scheme, parts.netloc, f"/{database_name}", parts.query, parts.fragment))

    def close(self) -> None:
        self.worker.close()

    def run(self) -> int:
        try:
            self._load_baseline()
            if self.args.mode == "dry-run":
                summary = self._run_dry_run()
            else:
                summary = self._run_apply()
            self._write_json("summary.json", summary)
            self.logger.info("Backfill %s completed for ids %s-%s", self.args.mode, self.args.id_from, self.args.id_to)
            return 0
        finally:
            self.close()

    def _load_baseline(self) -> None:
        self.cursor_snapshot = self._get_cursor_snapshot()
        self.range_rows = self._fetch_range_rows()
        self.employee_map = self.worker._fetch_employee_map(self.range_rows)
        self.existing_event_map = self._fetch_existing_event_details(self.range_rows)
        self.preexisting_conflicts = self._load_preexisting_conflicts()

    def _fetch_range_rows(self) -> list[dict[str, Any]]:
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
            WHERE id >= %s
              AND id <= %s
              AND event_kind = 'access_control'
            ORDER BY id
        """
        with self.worker.db.transaction():
            with self.worker.db.cursor() as cur:
                cur.execute(query, (self.args.id_from, self.args.id_to))
                rows = cur.fetchall()
        return rows

    def _get_cursor_snapshot(self) -> dict[str, Any]:
        rows = self.worker.odoo.search_read(
            "hr.biometric.sync.cursor",
            [["name", "=", self.args.cursor_name]],
            ["id", "name", "last_normalized_event_id", "last_event_occurred_at_utc", "last_success_at"],
            limit=1,
        )
        return rows[0] if rows else {}

    def _local_date(self, event_utc: datetime) -> date:
        return event_utc.astimezone(self.zone).date()

    def _local_day_bounds_utc(self, target_date: date) -> tuple[datetime, datetime]:
        start_local = datetime.combine(target_date, dt_time.min, tzinfo=self.zone)
        end_local = datetime.combine(target_date, dt_time.max, tzinfo=self.zone)
        return start_local.astimezone(UTC), end_local.astimezone(UTC)

    def _fetch_existing_event_details(self, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        ids = [int(row["id"]) for row in rows]
        if not ids:
            return {}
        existing_rows = self.worker.odoo.search_read(
            "hr.biometric.event",
            [["normalized_event_id", "in", ids]],
            ["id", "normalized_event_id", "sync_status", "attendance_id", "employee_id", "event_occurred_at_utc"],
        )
        return {int(row["normalized_event_id"]): row for row in existing_rows}

    def _load_preexisting_conflicts(self) -> dict[tuple[int, date], list[dict[str, Any]]]:
        employee_ids = sorted({employee["id"] for employee in self.employee_map.values() if employee})
        if not employee_ids or not self.range_rows:
            return {}

        local_dates = [self._local_date(row["event_occurred_at_utc"]) for row in self.range_rows]
        start_utc, _ = self._local_day_bounds_utc(min(local_dates))
        _, end_utc = self._local_day_bounds_utc(max(local_dates))
        rows = self.worker.odoo.search_read(
            "hr.attendance",
            [
                ["employee_id", "in", employee_ids],
                ["check_in", ">=", odoo_datetime(start_utc)],
                ["check_in", "<=", odoo_datetime(end_utc)],
            ],
            ["id", "employee_id", "check_in", "check_out", "biometric_source"],
            limit=5000,
            order="employee_id,check_in,id",
        )
        conflicts: dict[tuple[int, date], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            check_in_dt = parse_odoo_datetime(row.get("check_in"))
            if check_in_dt is None:
                continue
            local_date = self._local_date(check_in_dt)
            employee = row.get("employee_id")
            if not employee:
                continue
            conflicts[(employee[0], local_date)].append(row)
        return conflicts

    def _load_latest_accepted_before(self, before_utc: datetime) -> dict[int, SimAcceptedEvent]:
        rows = self.worker.odoo.search_read(
            "hr.biometric.event",
            [
                ["sync_status", "in", sorted(ACCEPTED_SYNC_STATUSES)],
                ["event_occurred_at_utc", "<", odoo_datetime(before_utc)],
            ],
            ["id", "employee_id", "attendance_id", "event_occurred_at_utc"],
            limit=5000,
            order="event_occurred_at_utc asc,id asc",
        )
        latest: dict[int, SimAcceptedEvent] = {}
        for row in rows:
            employee = row.get("employee_id")
            event_dt = parse_odoo_datetime(row.get("event_occurred_at_utc"))
            if not employee or event_dt is None:
                continue
            attendance = row.get("attendance_id")
            latest[employee[0]] = SimAcceptedEvent(
                event_id=row["id"],
                occurred_at_utc=event_dt,
                attendance_id=attendance[0] if attendance else None,
            )
        return latest

    def _load_open_attendance_before(self, before_utc: datetime) -> dict[int, PendingAttendanceState]:
        employee_ids = sorted({employee["id"] for employee in self.employee_map.values() if employee})
        if not employee_ids:
            return {}
        rows = self.worker.odoo.search_read(
            "hr.attendance",
            [["employee_id", "in", employee_ids], ["check_out", "=", False], ["check_in", "<", odoo_datetime(before_utc)]],
            ["id", "employee_id", "check_in", "biometric_checkin_event_id"],
            limit=1000,
            order="check_in asc,id asc",
        )
        open_attendance: dict[int, PendingAttendanceState] = {}
        for row in rows:
            employee = row.get("employee_id")
            check_in_dt = parse_odoo_datetime(row.get("check_in"))
            if not employee or check_in_dt is None:
                continue
            checkin_event = row.get("biometric_checkin_event_id")
            open_attendance[employee[0]] = PendingAttendanceState(
                local_date=self._local_date(check_in_dt),
                check_in_utc=check_in_dt,
                attendance_id=row["id"],
                checkin_event_id=checkin_event[0] if checkin_event else None,
            )
        return open_attendance

    def _find_latest_accepted_event_before(self, employee_id: int, before_utc: datetime) -> dict[str, Any] | None:
        rows = self.worker.odoo.search_read(
            "hr.biometric.event",
            [
                ["employee_id", "=", employee_id],
                ["sync_status", "in", sorted(ACCEPTED_SYNC_STATUSES)],
                ["event_occurred_at_utc", "<=", odoo_datetime(before_utc)],
            ],
            ["id", "event_occurred_at_utc", "attendance_id"],
            limit=1,
            order="event_occurred_at_utc desc,id desc",
        )
        return rows[0] if rows else None

    def _find_open_attendance_before(self, employee_id: int, before_utc: datetime) -> dict[str, Any] | None:
        rows = self.worker.odoo.search_read(
            "hr.attendance",
            [["employee_id", "=", employee_id], ["check_out", "=", False], ["check_in", "<=", odoo_datetime(before_utc)]],
            ["id", "check_in", "biometric_checkin_event_id"],
            limit=1,
            order="check_in desc,id desc",
        )
        return rows[0] if rows else None

    def _row_base(self, row: dict[str, Any], employee: dict[str, Any] | None) -> dict[str, Any]:
        local_dt = row["event_occurred_at_utc"].astimezone(self.zone)
        return {
            "normalized_event_id": int(row["id"]),
            "event_local_date": local_dt.date().isoformat(),
            "event_local_time": local_dt.strftime("%H:%M:%S"),
            "user_id_on_device": str(row.get("user_id_on_device") or ""),
            "device_id_resolved": row.get("device_id_resolved") or "",
            "employee_id": employee["id"] if employee else "",
            "employee_name": employee["name"] if employee else "",
        }

    def _simulate_rows(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        report_rows: list[dict[str, Any]] = []
        employee_not_found_rows: list[dict[str, Any]] = []
        conflict_rows: list[dict[str, Any]] = []
        summary_counts = Counter()
        by_day = defaultdict(Counter)

        if not self.range_rows:
            summary = self._build_summary(report_rows, employee_not_found_rows, conflict_rows, summary_counts, by_day)
            return report_rows, summary

        start_utc = min(row["event_occurred_at_utc"] for row in self.range_rows)
        last_accepted = self._load_latest_accepted_before(start_utc)
        open_attendance = self._load_open_attendance_before(start_utc)

        for row in self.range_rows:
            employee_key = str(row.get("user_id_on_device") or "").strip()
            employee = self.employee_map.get(employee_key)
            local_dt = row["event_occurred_at_utc"].astimezone(self.zone)
            local_date = local_dt.date()
            base = self._row_base(row, employee)
            existing_event = self.existing_event_map.get(int(row["id"]))

            if existing_event and existing_event["sync_status"] not in {"pending", "error"}:
                base["outcome"] = EXISTING_SYNCED_STATUS
                report_rows.append(base)
                summary_counts[EXISTING_SYNCED_STATUS] += 1
                by_day[local_date][EXISTING_SYNCED_STATUS] += 1
                continue

            if not employee_key:
                base["outcome"] = "error"
                base["message"] = "UserID vacío."
                report_rows.append(base)
                summary_counts["error"] += 1
                by_day[local_date]["error"] += 1
                continue

            if employee is None:
                base["outcome"] = "employee_not_found"
                base["message"] = "No existe empleado activo con ese employee_number."
                report_rows.append(base)
                employee_not_found_rows.append(base)
                summary_counts["employee_not_found"] += 1
                by_day[local_date]["employee_not_found"] += 1
                continue

            if row.get("granted") is not True:
                base["outcome"] = "denied_ignored"
                base["message"] = "Evento no autorizado."
                report_rows.append(base)
                summary_counts["denied_ignored"] += 1
                by_day[local_date]["denied_ignored"] += 1
                continue

            conflict_key = (employee["id"], local_date)
            if conflict_key in self.preexisting_conflicts:
                base["outcome"] = RANGE_CONFLICT_STATUS
                base["message"] = "Ya existen asistencias previas para empleado+día en Odoo."
                report_rows.append(base)
                conflict_rows.append(
                    base
                    | {
                        "existing_attendance_ids": ",".join(str(item["id"]) for item in self.preexisting_conflicts[conflict_key]),
                    }
                )
                summary_counts[RANGE_CONFLICT_STATUS] += 1
                by_day[local_date][RANGE_CONFLICT_STATUS] += 1
                continue

            previous = last_accepted.get(employee["id"])
            if previous:
                gap_seconds = (row["event_occurred_at_utc"] - previous.occurred_at_utc).total_seconds()
                if gap_seconds <= int(self.config["debounce_seconds"]):
                    base["outcome"] = "duplicate_ignored"
                    base["message"] = f"Dentro de debounce ({int(gap_seconds)}s)."
                    report_rows.append(base)
                    summary_counts["duplicate_ignored"] += 1
                    by_day[local_date]["duplicate_ignored"] += 1
                    continue

            current_open = open_attendance.get(employee["id"])
            if current_open and current_open.local_date < local_date:
                open_attendance.pop(employee["id"], None)
                current_open = None

            if current_open:
                base["outcome"] = "check_out_written"
                base["message"] = "Cierre de asistencia existente."
                report_rows.append(base)
                last_accepted[employee["id"]] = SimAcceptedEvent(
                    event_id=int(row["id"]),
                    occurred_at_utc=row["event_occurred_at_utc"],
                    attendance_id=current_open.attendance_id,
                )
                open_attendance.pop(employee["id"], None)
                summary_counts["check_out_written"] += 1
                by_day[local_date]["check_out_written"] += 1
                continue

            base["outcome"] = "check_in_created"
            base["message"] = "Creación de asistencia de entrada."
            report_rows.append(base)
            simulated_attendance_id = int(row["id"])
            open_attendance[employee["id"]] = PendingAttendanceState(
                local_date=local_date,
                check_in_utc=row["event_occurred_at_utc"],
                attendance_id=simulated_attendance_id,
            )
            last_accepted[employee["id"]] = SimAcceptedEvent(
                event_id=int(row["id"]),
                occurred_at_utc=row["event_occurred_at_utc"],
                attendance_id=simulated_attendance_id,
            )
            summary_counts["check_in_created"] += 1
            by_day[local_date]["check_in_created"] += 1

        summary = self._build_summary(report_rows, employee_not_found_rows, conflict_rows, summary_counts, by_day)
        self._write_csv("predicted_rows.csv", report_rows)
        self._write_csv("employee_not_found.csv", employee_not_found_rows)
        self._write_csv("conflicts.csv", conflict_rows)
        self._write_csv("by_day.csv", self._by_day_rows(by_day))
        return report_rows, summary

    def _build_summary(
        self,
        report_rows: list[dict[str, Any]],
        employee_not_found_rows: list[dict[str, Any]],
        conflict_rows: list[dict[str, Any]],
        status_counts: Counter,
        by_day: dict[date, Counter],
        apply_counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        local_dates = [self._local_date(row["event_occurred_at_utc"]) for row in self.range_rows]
        unique_employee_days = {
            (str(row.get("user_id_on_device") or "").strip(), self._local_date(row["event_occurred_at_utc"]))
            for row in self.range_rows
        }
        unique_missing_employee_days = {
            (str(row.get("user_id_on_device") or "").strip(), self._local_date(row["event_occurred_at_utc"]))
            for row in self.range_rows
            if str(row.get("user_id_on_device") or "").strip()
            and self.employee_map.get(str(row.get("user_id_on_device") or "").strip()) is None
        }
        unique_mapped_days = {
            (self.employee_map[str(row.get("user_id_on_device") or "").strip()]["id"], self._local_date(row["event_occurred_at_utc"]))
            for row in self.range_rows
            if self.employee_map.get(str(row.get("user_id_on_device") or "").strip())
        }
        return {
            "mode": self.args.mode,
            "id_range": {"from": self.args.id_from, "to": self.args.id_to},
            "local_date_range": {
                "from": min(local_dates).isoformat() if local_dates else None,
                "to": max(local_dates).isoformat() if local_dates else None,
            },
            "cursor_snapshot": self.cursor_snapshot,
            "baseline": {
                "normalized_event_total": len(self.range_rows),
                "access_control_total": len(self.range_rows),
                "employee_day_total": len(unique_employee_days),
                "employee_day_mapped_active_total": len(unique_mapped_days),
                "employee_not_found_total": len(unique_missing_employee_days),
                "employee_not_found_event_total": len(employee_not_found_rows),
                "conflict_total": len(conflict_rows),
                "with_device_total": sum(1 for row in self.range_rows if row.get("device_id_resolved")),
            },
            "status_counts": dict(status_counts),
            "apply_counts": apply_counts or {},
            "generated_at_utc": datetime.now(UTC).isoformat(),
        }

    def _by_day_rows(self, by_day: dict[date, Counter]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for local_date in sorted(by_day):
            counter = by_day[local_date]
            rows.append(
                {
                    "local_date": local_date.isoformat(),
                    "check_in_created": counter.get("check_in_created", 0),
                    "check_out_written": counter.get("check_out_written", 0),
                    "duplicate_ignored": counter.get("duplicate_ignored", 0),
                    "employee_not_found": counter.get("employee_not_found", 0),
                    "denied_ignored": counter.get("denied_ignored", 0),
                    "error": counter.get("error", 0),
                    "already_synced": counter.get(EXISTING_SYNCED_STATUS, 0),
                    "conflict_preserved": counter.get(RANGE_CONFLICT_STATUS, 0),
                }
            )
        return rows

    def _write_csv(self, filename: str, rows: list[dict[str, Any]]) -> None:
        path = self.args.report_dir / filename
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        fieldnames: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        path = self.args.report_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    def _run_dry_run(self) -> dict[str, Any]:
        _, summary = self._simulate_rows()
        return summary

    def _run_apply(self) -> dict[str, Any]:
        self.worker.logger.info("Starting attendance backfill apply for ids %s-%s", self.args.id_from, self.args.id_to)
        run_id = self.worker.odoo.create(
            "hr.biometric.sync.run",
            {
                "name": f"BACKFILL {self.args.id_from}-{self.args.id_to}",
                "run_type": "backfill",
                "status": "running",
                "started_at": odoo_datetime(datetime.now(UTC)),
                "last_normalized_event_id": self.args.id_to,
                "message": f"Backfill apply for ids {self.args.id_from}-{self.args.id_to}",
            },
        )
        apply_counts = Counter()
        status_counts = Counter()
        apply_rows: list[dict[str, Any]] = []
        employee_not_found_rows: list[dict[str, Any]] = []
        conflict_rows: list[dict[str, Any]] = []
        by_day = defaultdict(Counter)
        employee_by_id = {employee["id"]: employee for employee in self.employee_map.values() if employee}
        start_utc = min((row["event_occurred_at_utc"] for row in self.range_rows), default=None)
        last_accepted = self._load_latest_accepted_before(start_utc) if start_utc else {}
        open_attendance = self._load_open_attendance_before(start_utc) if start_utc else {}

        try:
            for row in self.range_rows:
                employee_key = str(row.get("user_id_on_device") or "").strip()
                employee = self.employee_map.get(employee_key)
                local_dt = row["event_occurred_at_utc"].astimezone(self.zone)
                local_date = local_dt.date()
                base = self._row_base(row, employee)
                existing_event = self.existing_event_map.get(int(row["id"]))

                if existing_event and existing_event["sync_status"] not in {"pending", "error"}:
                    base["outcome"] = EXISTING_SYNCED_STATUS
                    apply_rows.append(base)
                    apply_counts["skipped_count"] += 1
                    status_counts[EXISTING_SYNCED_STATUS] += 1
                    by_day[local_date][EXISTING_SYNCED_STATUS] += 1
                    continue

                if not employee_key:
                    self.worker._upsert_event_record(
                        row=row,
                        employee=None,
                        existing_event=existing_event,
                        config=self.config,
                        sync_status="error",
                        attendance_action="error",
                        attendance_id=False,
                        message="UserID is empty for access_control.",
                        dedupe_reference_event_id=False,
                        auto_closed=False,
                        auto_close_reason=False,
                    )
                    base["outcome"] = "error"
                    base["message"] = "UserID vacío."
                    apply_rows.append(base)
                    apply_counts["processed_count"] += 1
                    apply_counts["error_count"] += 1
                    status_counts["error"] += 1
                    by_day[local_date]["error"] += 1
                    continue

                if employee is None:
                    self.worker._upsert_event_record(
                        row=row,
                        employee=None,
                        existing_event=existing_event,
                        config=self.config,
                        sync_status="employee_not_found",
                        attendance_action="employee_not_found",
                        attendance_id=False,
                        message="No active employee matched by employee_number.",
                        dedupe_reference_event_id=False,
                        auto_closed=False,
                        auto_close_reason=False,
                    )
                    base["outcome"] = "employee_not_found"
                    base["message"] = "No existe empleado activo con ese employee_number."
                    apply_rows.append(base)
                    employee_not_found_rows.append(base)
                    apply_counts["processed_count"] += 1
                    apply_counts["skipped_count"] += 1
                    status_counts["employee_not_found"] += 1
                    by_day[local_date]["employee_not_found"] += 1
                    continue

                if row.get("granted") is not True:
                    self.worker._upsert_event_record(
                        row=row,
                        employee=employee,
                        existing_event=existing_event,
                        config=self.config,
                        sync_status="denied_ignored",
                        attendance_action="denied_ignored",
                        attendance_id=False,
                        message="Access control event was not granted.",
                        dedupe_reference_event_id=False,
                        auto_closed=False,
                        auto_close_reason=False,
                    )
                    base["outcome"] = "denied_ignored"
                    apply_rows.append(base)
                    apply_counts["processed_count"] += 1
                    apply_counts["created_count"] += 1
                    status_counts["denied_ignored"] += 1
                    by_day[local_date]["denied_ignored"] += 1
                    continue

                conflict_key = (employee["id"], local_date)
                if conflict_key in self.preexisting_conflicts:
                    base["outcome"] = RANGE_CONFLICT_STATUS
                    base["message"] = "Ya existen asistencias previas para empleado+día en Odoo."
                    apply_rows.append(base)
                    conflict_rows.append(
                        base
                        | {
                            "existing_attendance_ids": ",".join(str(item["id"]) for item in self.preexisting_conflicts[conflict_key]),
                        }
                    )
                    apply_counts["skipped_count"] += 1
                    status_counts[RANGE_CONFLICT_STATUS] += 1
                    by_day[local_date][RANGE_CONFLICT_STATUS] += 1
                    continue

                previous = last_accepted.get(employee["id"])
                if previous:
                    gap_seconds = (row["event_occurred_at_utc"] - previous.occurred_at_utc).total_seconds()
                    if gap_seconds <= int(self.config["debounce_seconds"]):
                        self.worker._upsert_event_record(
                            row=row,
                            employee=employee,
                            existing_event=existing_event,
                            config=self.config,
                            sync_status="duplicate_ignored",
                            attendance_action="duplicate_ignored",
                            attendance_id=previous.attendance_id or False,
                            message=f"Duplicate within debounce window ({int(gap_seconds)}s).",
                            dedupe_reference_event_id=previous.event_id,
                            auto_closed=False,
                            auto_close_reason=False,
                        )
                        outcome = "duplicate_ignored"
                        base["outcome"] = outcome
                        apply_rows.append(base)
                        apply_counts["processed_count"] += 1
                        apply_counts["updated_count"] += 1
                        status_counts[outcome] += 1
                        by_day[local_date][outcome] += 1
                        continue

                current_open = open_attendance.get(employee["id"])
                if current_open and current_open.local_date < local_date:
                    auto_close_reason = "auto_close_before_new_day_v1"
                    auto_close_msg = "Attendance auto-closed by backfill before next local day."
                    attendance_id = self._materialize_auto_close(current_open, employee, auto_close_reason, auto_close_msg)
                    if previous and previous.attendance_id is None:
                        last_accepted[employee["id"]] = SimAcceptedEvent(
                            event_id=previous.event_id,
                            occurred_at_utc=previous.occurred_at_utc,
                            attendance_id=attendance_id,
                        )
                    open_attendance.pop(employee["id"], None)
                    current_open = None

                if current_open:
                    outcome, attendance_id, event_id = self._materialize_checkout(current_open, row, employee, existing_event)
                    last_accepted[employee["id"]] = SimAcceptedEvent(
                        event_id=event_id,
                        occurred_at_utc=row["event_occurred_at_utc"],
                        attendance_id=attendance_id,
                    )
                    open_attendance.pop(employee["id"], None)
                else:
                    event_id = self._ensure_pending_event(row, employee, existing_event)
                    open_attendance[employee["id"]] = PendingAttendanceState(
                        local_date=local_date,
                        check_in_utc=row["event_occurred_at_utc"],
                        checkin_event_id=event_id,
                        checkin_row=row,
                    )
                    last_accepted[employee["id"]] = SimAcceptedEvent(
                        event_id=event_id,
                        occurred_at_utc=row["event_occurred_at_utc"],
                        attendance_id=None,
                    )
                    outcome = "check_in_created"

                base["outcome"] = outcome
                apply_rows.append(base)
                apply_counts["processed_count"] += 1
                status_counts[outcome] += 1
                by_day[local_date][outcome] += 1
                if outcome == "check_in_created":
                    apply_counts["created_count"] += 1
                elif outcome in {"check_out_written", "duplicate_ignored"}:
                    apply_counts["updated_count"] += 1
                elif outcome == "employee_not_found":
                    apply_counts["skipped_count"] += 1
                else:
                    apply_counts["skipped_count"] += 1

            today_local = datetime.now(self.zone).date()
            for employee_id, pending_state in list(open_attendance.items()):
                if pending_state.checkin_row is None:
                    continue
                if pending_state.local_date >= today_local:
                    continue
                employee = employee_by_id.get(employee_id)
                if not employee:
                    continue
                self._materialize_auto_close(
                    pending_state,
                    employee,
                    "auto_close_eod_v1",
                    "Attendance auto-closed by backfill end-of-day rule.",
                )

            summary = self._build_summary(
                apply_rows,
                employee_not_found_rows,
                conflict_rows,
                status_counts,
                by_day,
                apply_counts=dict(apply_counts),
            )
            cursor_after = self._get_cursor_snapshot()
            summary["cursor_after"] = cursor_after
            if cursor_after.get("last_normalized_event_id") != self.cursor_snapshot.get("last_normalized_event_id"):
                raise RuntimeError("El cursor principal cambió durante el backfill.")

            self.worker.odoo.write(
                "hr.biometric.sync.run",
                [run_id],
                {
                    "status": "success",
                    "finished_at": odoo_datetime(datetime.now(UTC)),
                    "processed_count": apply_counts["processed_count"],
                    "created_count": apply_counts["created_count"],
                    "updated_count": apply_counts["updated_count"],
                    "skipped_count": apply_counts["skipped_count"],
                    "error_count": apply_counts["error_count"],
                    "message": (
                        f"Backfill {self.args.id_from}-{self.args.id_to}: "
                        f"processed={apply_counts['processed_count']} skipped={apply_counts['skipped_count']} "
                        f"errors={apply_counts['error_count']}"
                    ),
                },
            )
            self._write_csv("predicted_rows.csv", apply_rows)
            self._write_csv("employee_not_found.csv", employee_not_found_rows)
            self._write_csv("conflicts.csv", conflict_rows)
            self._write_csv("by_day.csv", self._by_day_rows(by_day))
            return summary
        except Exception as exc:  # noqa: BLE001
            self.worker.odoo.write(
                "hr.biometric.sync.run",
                [run_id],
                {
                    "status": "failed",
                    "finished_at": odoo_datetime(datetime.now(UTC)),
                    "processed_count": apply_counts["processed_count"],
                    "created_count": apply_counts["created_count"],
                    "updated_count": apply_counts["updated_count"],
                    "skipped_count": apply_counts["skipped_count"],
                    "error_count": apply_counts["error_count"] + 1,
                    "message": f"{type(exc).__name__}: {exc}",
                },
            )
            raise

    def _ensure_pending_event(
        self,
        row: dict[str, Any],
        employee: dict[str, Any],
        existing_event: dict[str, Any] | None,
    ) -> int:
        event_id, _ = self.worker._upsert_event_record(
            row=row,
            employee=employee,
            existing_event=existing_event,
            config=self.config,
            sync_status="pending",
            attendance_action=False,
            attendance_id=False,
            message="Pending attendance decision.",
            dedupe_reference_event_id=False,
            auto_closed=False,
            auto_close_reason=False,
            return_record_id=True,
        )
        return event_id

    def _materialize_checkout(
        self,
        pending_state: PendingAttendanceState,
        row: dict[str, Any],
        employee: dict[str, Any],
        existing_event: dict[str, Any] | None,
    ) -> tuple[str, int, int]:
        attendance_context = {"skip_devlyn_journey_rebuild": True}
        checkout_event_id = self._ensure_pending_event(row, employee, existing_event)
        checkout_utc = row["event_occurred_at_utc"]

        if pending_state.attendance_id:
            attendance_id = pending_state.attendance_id
            self.worker._write_attendance(
                attendance_id,
                {
                    "check_out": odoo_datetime(checkout_utc),
                    "biometric_checkout_event_id": checkout_event_id,
                    "biometric_source": self.config["source_mode_label"],
                    "biometric_inference_mode": self.settings.inference_mode,
                },
                context=attendance_context,
            )
        else:
            attendance_id = self.worker.odoo.create(
                "hr.attendance",
                {
                    "employee_id": employee["id"],
                    "check_in": odoo_datetime(pending_state.check_in_utc),
                    "check_out": odoo_datetime(checkout_utc),
                    "biometric_source": self.config["source_mode_label"],
                    "biometric_inference_mode": self.settings.inference_mode,
                    "biometric_checkin_event_id": pending_state.checkin_event_id,
                    "biometric_checkout_event_id": checkout_event_id,
                },
                context=attendance_context,
            )
            self.worker.odoo.write(
                "hr.biometric.event",
                [pending_state.checkin_event_id],
                {
                    "sync_status": "check_in_created",
                    "attendance_action": "check_in_created",
                    "attendance_id": attendance_id,
                    "message": "Attendance check-in created by backfill raw toggle v1.",
                },
            )

        self.worker.odoo.write(
            "hr.biometric.event",
            [checkout_event_id],
            {
                "sync_status": "check_out_written",
                "attendance_action": "check_out_written",
                "attendance_id": attendance_id,
                "message": "Open attendance closed by backfill raw toggle v1.",
            },
        )
        return "check_out_written", attendance_id, checkout_event_id

    def _materialize_auto_close(
        self,
        pending_state: PendingAttendanceState,
        employee: dict[str, Any],
        auto_close_reason: str,
        message: str,
    ) -> int:
        attendance_context = {"skip_devlyn_journey_rebuild": True}
        close_dt = local_end_of_day_utc(pending_state.local_date, self.config["timezone_name"])

        if pending_state.attendance_id:
            attendance_id = pending_state.attendance_id
            self.worker._write_attendance(
                attendance_id,
                {
                    "check_out": odoo_datetime(close_dt),
                    "biometric_auto_closed": True,
                    "biometric_auto_close_reason": auto_close_reason,
                },
                context=attendance_context,
            )
        else:
            attendance_id = self.worker.odoo.create(
                "hr.attendance",
                {
                    "employee_id": employee["id"],
                    "check_in": odoo_datetime(pending_state.check_in_utc),
                    "check_out": odoo_datetime(close_dt),
                    "biometric_source": self.config["source_mode_label"],
                    "biometric_inference_mode": self.settings.inference_mode,
                    "biometric_checkin_event_id": pending_state.checkin_event_id,
                    "biometric_auto_closed": True,
                    "biometric_auto_close_reason": auto_close_reason,
                },
                context=attendance_context,
            )

        if pending_state.checkin_event_id:
            self.worker.odoo.write(
                "hr.biometric.event",
                [pending_state.checkin_event_id],
                {
                    "sync_status": "check_in_created",
                    "attendance_action": "check_in_created",
                    "attendance_id": attendance_id,
                    "attendance_auto_closed": True,
                    "auto_close_reason": auto_close_reason,
                    "message": message,
                },
            )
        return attendance_id


def parse_args() -> BackfillArgs:
    parser = argparse.ArgumentParser(description="Backfill controlado de asistencias Dahua hacia Odoo")
    parser.add_argument("--mode", choices=["dry-run", "apply"], required=True)
    parser.add_argument("--id-from", type=int, required=True)
    parser.add_argument("--id-to", type=int, required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--odoo-db", default="devlyn_com")
    parser.add_argument("--biometric-db", default="biometric_ingest")
    parser.add_argument("--cursor-name", default="main")
    parser.add_argument("--batch-size", type=int, default=100)
    ns = parser.parse_args()
    return BackfillArgs(
        mode=ns.mode,
        id_from=ns.id_from,
        id_to=ns.id_to,
        report_dir=Path(ns.report_dir),
        odoo_db=ns.odoo_db,
        biometric_db=ns.biometric_db,
        cursor_name=ns.cursor_name,
        batch_size=max(1, ns.batch_size),
    )


def main() -> int:
    args = parse_args()
    runner = AttendanceSyncBackfill(args)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
