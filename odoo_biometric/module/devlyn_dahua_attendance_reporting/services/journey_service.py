from __future__ import annotations

import json
from datetime import date as date_cls

from odoo import fields, models
from odoo.exceptions import ValidationError

from .report_utils import (
    DAY_STATE_LABELS,
    SegmentSnapshot,
    build_segment_payloads,
    derive_segment_center_code,
    extract_center_code,
    to_local_datetime,
    utc_bounds_for_local_dates,
)


DEFAULT_HISTORY_START = date_cls(2026, 3, 20)


class DevlynAttendanceJourneyServiceModel(models.AbstractModel):
    _name = "devlyn.attendance.journey.service"
    _description = "Devlyn Attendance Journey Service"

    def get_timezone_name(self) -> str:
        config = self.env["hr.biometric.sync.config"].search([], limit=1)
        return config.timezone_name or "America/Mexico_City"

    def day_state_label(self, value: str | None) -> str:
        return DAY_STATE_LABELS.get(value or "", "")

    def _normalize_date(self, value) -> date_cls:
        normalized = fields.Date.to_date(value)
        if not normalized:
            raise ValidationError("La fecha es requerida para reconstruir jornadas.")
        return normalized

    def _validate_range(self, date_from, date_to) -> tuple[date_cls, date_cls]:
        normalized_from = self._normalize_date(date_from)
        normalized_to = self._normalize_date(date_to)
        if normalized_to < normalized_from:
            raise ValidationError("La fecha final no puede ser menor a la fecha inicial.")
        return normalized_from, normalized_to

    def _branch_by_center(self) -> dict[str, object]:
        branches = self.env["devlyn.catalog.branch"].search([])
        return {record.center_code: record for record in branches}

    def build_segment_snapshot(self, attendance, tz_name: str | None = None, branch_by_center=None) -> SegmentSnapshot | None:
        timezone_name = tz_name or self.get_timezone_name()
        local_check_in = to_local_datetime(attendance.check_in, timezone_name)
        if not local_check_in:
            return None
        local_check_out = to_local_datetime(attendance.check_out, timezone_name)
        branch_lookup = branch_by_center or self._branch_by_center()
        center_code = derive_segment_center_code(
            attendance.biometric_checkin_event_id.device_id_resolved or None,
            attendance.biometric_checkout_event_id.device_id_resolved or None,
        )
        branch = branch_lookup.get(center_code) if center_code else None
        return SegmentSnapshot(
            attendance_id=attendance.id,
            check_in_local=local_check_in,
            check_out_local=local_check_out,
            worked_minutes=max(0, round((attendance.worked_hours or 0.0) * 60)),
            auto_closed=bool(attendance.biometric_auto_closed),
            center_code=(branch.center_code if branch else center_code or extract_center_code(
                attendance.biometric_checkin_event_id.device_id_resolved
                or attendance.biometric_checkout_event_id.device_id_resolved
                or None
            )),
            branch_id=branch.id if branch else None,
        )

    def preview_journey(self, employee_id: int, local_date) -> dict:
        normalized_date = self._normalize_date(local_date)
        timezone_name = self.get_timezone_name()
        start_utc, end_utc = utc_bounds_for_local_dates(normalized_date, normalized_date, timezone_name)
        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", employee_id),
                ("biometric_source", "=", "biometric_v1"),
                ("check_in", ">=", start_utc),
                ("check_in", "<", end_utc),
            ],
            order="check_in, id",
        )
        existing = self.env["devlyn.attendance.journey"].search(
            [("employee_id", "=", employee_id), ("local_date", "=", normalized_date)],
            limit=1,
        )
        if not attendances:
            return {
                "employee_id": employee_id,
                "local_date": normalized_date.isoformat(),
                "action": "delete" if existing else "noop",
                "segment_count": 0,
                "intermittence_count": 0,
                "total_gap_minutes": 0,
                "day_state": "closed",
                "has_auto_close": False,
                "has_after_close_review": False,
            }

        branch_by_center = self._branch_by_center()
        snapshots = [
            snapshot
            for snapshot in (
                self.build_segment_snapshot(attendance, timezone_name, branch_by_center)
                for attendance in attendances
            )
            if snapshot
        ]
        payloads, summary = build_segment_payloads(snapshots)
        has_after_close_review = bool(
            self.env["hr.biometric.event"].search_count(
                [
                    ("employee_id", "=", employee_id),
                    ("event_local_date", "=", normalized_date),
                    ("sync_status", "=", "after_close_review"),
                ]
            )
        )
        return {
            "employee_id": employee_id,
            "local_date": normalized_date.isoformat(),
            "action": "update" if existing else "create",
            "segment_count": summary["segment_count"],
            "intermittence_count": max(summary["segment_count"] - 1, 0),
            "total_gap_minutes": summary["total_gap_minutes"],
            "day_state": summary["day_state"],
            "has_auto_close": summary["has_auto_close"],
            "has_after_close_review": has_after_close_review,
            "segments": payloads,
        }

    def rebuild_journey(self, employee_id: int, local_date) -> dict:
        preview = self.preview_journey(employee_id, local_date)
        journey_model = self.env["devlyn.attendance.journey"]
        segment_model = self.env["devlyn.attendance.journey.segment"]
        normalized_date = self._normalize_date(local_date)
        journey = journey_model.search(
            [("employee_id", "=", employee_id), ("local_date", "=", normalized_date)],
            limit=1,
        )

        if preview["action"] == "noop":
            return preview | {"journey_id": False, "segment_rows": 0}

        if preview["action"] == "delete":
            deleted_segments = len(journey.segment_ids) if journey else 0
            if journey:
                journey.segment_ids.unlink()
                journey.unlink()
            return preview | {"journey_id": False, "segment_rows": 0, "deleted_segments": deleted_segments}

        journey_vals = {
            "employee_id": employee_id,
            "local_date": normalized_date,
            "segment_count": preview["segment_count"],
            "intermittence_count": preview["intermittence_count"],
            "total_gap_minutes": preview["total_gap_minutes"],
            "day_state": preview["day_state"],
            "has_auto_close": preview["has_auto_close"],
            "has_after_close_review": preview["has_after_close_review"],
            "rebuilt_at": fields.Datetime.now(),
        }
        if journey:
            journey.segment_ids.unlink()
            journey.write(journey_vals)
        else:
            journey = journey_model.create(journey_vals)

        segment_rows = preview.get("segments", [])
        for segment_vals in segment_rows:
            segment_model.create(segment_vals | {"journey_id": journey.id})
        return preview | {"journey_id": journey.id, "segment_rows": len(segment_rows)}

    def rebuild_key_pairs(self, key_pairs: set[tuple[int, object]]) -> None:
        for employee_id, local_date in sorted(key_pairs, key=lambda item: (item[1], item[0])):
            self.rebuild_journey(employee_id, local_date)

    def rebuild_journeys(
        self,
        date_from,
        date_to,
        employee_ids=None,
        *,
        batch_size: int = 500,
        run_type: str = "repair",
        mode: str = "apply",
        commit: bool | None = None,
    ) -> dict:
        return self.run_batch(
            run_type=run_type,
            mode=mode,
            date_from=date_from,
            date_to=date_to,
            employee_ids=employee_ids,
            batch_size=batch_size,
            commit=commit,
        )

    def _collect_range_keys(self, date_from, date_to, employee_ids=None) -> list[tuple[int, date_cls]]:
        normalized_from, normalized_to = self._validate_range(date_from, date_to)
        timezone_name = self.get_timezone_name()
        start_utc, end_utc = utc_bounds_for_local_dates(normalized_from, normalized_to, timezone_name)
        attendance_domain = [
            ("biometric_source", "=", "biometric_v1"),
            ("check_in", ">=", start_utc),
            ("check_in", "<", end_utc),
        ]
        journey_domain = [("local_date", ">=", normalized_from), ("local_date", "<=", normalized_to)]
        if employee_ids:
            attendance_domain.append(("employee_id", "in", employee_ids))
            journey_domain.append(("employee_id", "in", employee_ids))
        attendances = self.env["hr.attendance"].search(attendance_domain, order="employee_id, check_in, id")
        keys: set[tuple[int, date_cls]] = set()
        for attendance in attendances:
            local_check_in = to_local_datetime(attendance.check_in, timezone_name)
            if not local_check_in:
                continue
            keys.add((attendance.employee_id.id, local_check_in.date()))
        for journey in self.env["devlyn.attendance.journey"].search(journey_domain):
            keys.add((journey.employee_id.id, journey.local_date))
        return sorted(keys, key=lambda item: (item[1], item[0]))

    def run_batch(
        self,
        *,
        run_type: str = "backfill",
        mode: str = "dry_run",
        date_from=None,
        date_to=None,
        employee_ids=None,
        batch_size: int = 500,
        commit: bool | None = None,
    ) -> dict:
        normalized_from, normalized_to = self._validate_range(date_from or DEFAULT_HISTORY_START, date_to or fields.Date.today())
        selected_employee_ids = sorted(set(employee_ids or []))
        run_mode = "dry_run" if mode in {"dry_run", "dry-run"} else "apply"
        should_commit = bool(run_mode == "apply") if commit is None else bool(commit)
        run_vals = {
            "name": f"{run_type.upper()} {normalized_from.isoformat()} {normalized_to.isoformat()}",
            "run_type": run_type,
            "mode": run_mode,
            "status": "running",
            "date_from": normalized_from,
            "date_to": normalized_to,
            "batch_size": max(1, int(batch_size or 500)),
            "employee_filter_json": json.dumps(selected_employee_ids),
            "message": "Running.",
        }
        run = self.env["devlyn.attendance.journey.run"].create(run_vals)
        if should_commit:
            self.env.cr.commit()

        keys = self._collect_range_keys(normalized_from, normalized_to, selected_employee_ids)
        stats = {
            "key_count": len(keys),
            "processed_count": 0,
            "created_count": 0,
            "updated_count": 0,
            "deleted_count": 0,
            "segment_count": 0,
            "intermittence_count": 0,
            "error_count": 0,
        }
        try:
            for index, (employee_id, local_date) in enumerate(keys, start=1):
                preview = self.preview_journey(employee_id, local_date)
                stats["processed_count"] += 1
                stats["intermittence_count"] += preview["intermittence_count"]
                if preview["action"] == "create":
                    stats["created_count"] += 1
                elif preview["action"] == "update":
                    stats["updated_count"] += 1
                elif preview["action"] == "delete":
                    stats["deleted_count"] += 1
                stats["segment_count"] += preview.get("segment_count", 0)
                if run_mode == "apply":
                    self.rebuild_journey(employee_id, local_date)
                if should_commit and index % max(1, int(batch_size or 500)) == 0:
                    self.env.cr.commit()

            summary = {
                "run_id": run.id,
                "run_type": run_type,
                "mode": run_mode,
                "date_from": normalized_from.isoformat(),
                "date_to": normalized_to.isoformat(),
                "employee_ids": selected_employee_ids,
            } | stats
            run.write(
                {
                    "status": "success",
                    "finished_at": fields.Datetime.now(),
                    "message": "Completed successfully.",
                    "summary_json": summary,
                }
                | stats
            )
            if should_commit:
                self.env.cr.commit()
            return summary
        except Exception as exc:  # noqa: BLE001
            run.write(
                {
                    "status": "failed",
                    "finished_at": fields.Datetime.now(),
                    "error_count": stats["error_count"] + 1,
                    "message": f"{type(exc).__name__}: {exc}",
                    "summary_json": stats,
                }
                | stats
            )
            if should_commit:
                self.env.cr.commit()
            raise
