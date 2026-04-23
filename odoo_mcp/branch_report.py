from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo_mcp.backends import OdooBackend


def extract_center_code(device_id: str | None) -> str | None:
    if not device_id:
        return None
    candidate = device_id.strip().upper()
    if not candidate.startswith("DEVLYN_"):
        return None
    tail = candidate.split("_", 2)
    if len(tail) < 2:
        return None
    return tail[1] or None


def choose_center_code(center_codes: list[str | None]) -> str | None:
    resolved = {code for code in center_codes if code}
    if len(resolved) == 1:
        return next(iter(resolved))
    return None


def choose_timezone(name: str | None, fallback: str) -> ZoneInfo:
    for candidate in [name, fallback, "UTC"]:
        try:
            return ZoneInfo(candidate or "UTC")
        except Exception:
            continue
    return ZoneInfo("UTC")


def to_local_datetime(value: str | None, tz_name: str | None, fallback_timezone: str) -> datetime | None:
    if not value:
        return None
    zone = choose_timezone(tz_name, fallback_timezone)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if "T" in value else datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(zone)


def utc_bounds_for_local_dates(date_from: date, date_to: date, tz_name: str | None, fallback_timezone: str) -> tuple[str, str]:
    zone = choose_timezone(tz_name, fallback_timezone)
    start_local = datetime.combine(date_from, time.min, tzinfo=zone)
    end_local = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=zone)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
        end_local.astimezone(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
    )


def hours_to_hhmm(hours_value: float | int | None) -> str:
    if not hours_value:
        return "00:00"
    total_minutes = max(0, round(float(hours_value) * 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


class BranchAttendanceReportService:
    def __init__(self, odoo_backend: OdooBackend, fallback_timezone: str):
        self.odoo = odoo_backend
        self.fallback_timezone = fallback_timezone

    def _row_matches_filters(
        self,
        row: dict,
        *,
        resolution_scope: str,
        region_ids: set[int],
        zone_ids: set[int],
        district_ids: set[int],
        branch_ids: set[int],
        format_ids: set[int],
        status_ids: set[int],
        optical_level_ids: set[int],
    ) -> bool:
        branch = row["branch"]
        if resolution_scope == "mapped_only" and not branch:
            return False
        if resolution_scope == "sin_sucursal_only" and branch:
            return False

        filter_pairs = [
            (region_ids, "region_id"),
            (zone_ids, "zone_id"),
            (district_ids, "district_id"),
            (branch_ids, "branch_id"),
            (format_ids, "format_id"),
            (status_ids, "status_id"),
            (optical_level_ids, "optical_level_id"),
        ]
        for selected, field_name in filter_pairs:
            if not selected:
                continue
            if not branch:
                return False
            if row[field_name] not in selected:
                return False
        return True

    def build_rows(
        self,
        *,
        date_from: date,
        date_to: date,
        employee_ids: list[int] | None,
        resolution_scope: str,
        region_ids: list[int] | None,
        zone_ids: list[int] | None,
        district_ids: list[int] | None,
        branch_ids: list[int] | None,
        format_ids: list[int] | None,
        status_ids: list[int] | None,
        optical_level_ids: list[int] | None,
    ) -> tuple[list[dict], str]:
        timezone_name = self.odoo.get_timezone_name(self.fallback_timezone)
        start_utc, end_utc = utc_bounds_for_local_dates(date_from, date_to, timezone_name, self.fallback_timezone)
        domain: list = [
            ("biometric_source", "=", "biometric_v1"),
            ("check_in", ">=", start_utc),
            ("check_in", "<", end_utc),
        ]
        if employee_ids:
            domain.append(("employee_id", "in", employee_ids))

        attendances = self.odoo.search_read(
            "hr.attendance",
            domain,
            fields=self.odoo.existing_fields(
                "hr.attendance",
                [
                    "id",
                    "employee_id",
                    "check_in",
                    "check_out",
                    "worked_hours",
                    "biometric_source",
                    "biometric_checkin_event_id",
                    "biometric_checkout_event_id",
                ],
            ),
            limit=20000,
            order="employee_id, check_in, id",
        )

        event_ids: set[int] = set()
        employee_id_set: set[int] = set()
        for attendance in attendances:
            employee = attendance.get("employee_id")
            if isinstance(employee, dict) and employee.get("id"):
                employee_id_set.add(int(employee["id"]))
            for field_name in ("biometric_checkin_event_id", "biometric_checkout_event_id"):
                value = attendance.get(field_name)
                if isinstance(value, dict) and value.get("id"):
                    event_ids.add(int(value["id"]))

        employee_map = {
            int(row["id"]): row
            for row in self.odoo.read(
                "hr.employee",
                sorted(employee_id_set),
                self.odoo.existing_fields("hr.employee", ["id", "name", "employee_number"]),
            )
        }
        event_map = {
            int(row["id"]): row
            for row in self.odoo.read(
                "hr.biometric.event",
                sorted(event_ids),
                self.odoo.existing_fields("hr.biometric.event", ["id", "device_id_resolved"]),
            )
        }

        catalogs = self.odoo.get_devlyn_catalogs()
        branch_by_center = {row["center_code"]: row for row in catalogs["branches"]}

        grouped: dict[tuple[int, date], dict] = {}
        for attendance in attendances:
            employee = attendance.get("employee_id") or {}
            employee_id = employee.get("id")
            if not employee_id:
                continue
            local_check_in = to_local_datetime(attendance.get("check_in"), timezone_name, self.fallback_timezone)
            if not local_check_in:
                continue
            local_check_out = to_local_datetime(attendance.get("check_out"), timezone_name, self.fallback_timezone)

            bucket = grouped.setdefault(
                (int(employee_id), local_check_in.date()),
                {
                    "employee_id": int(employee_id),
                    "date": local_check_in.date(),
                    "first_check_in": local_check_in,
                    "last_check_out": local_check_out,
                    "worked_hours": 0.0,
                    "device_ids": [],
                },
            )
            if local_check_in < bucket["first_check_in"]:
                bucket["first_check_in"] = local_check_in
            if local_check_out and (
                bucket["last_check_out"] is None or local_check_out > bucket["last_check_out"]
            ):
                bucket["last_check_out"] = local_check_out
            bucket["worked_hours"] += float(attendance.get("worked_hours") or 0.0)
            for field_name in ("biometric_checkin_event_id", "biometric_checkout_event_id"):
                relation = attendance.get(field_name) or {}
                event = event_map.get(int(relation["id"])) if relation.get("id") else None
                bucket["device_ids"].append((event or {}).get("device_id_resolved"))

        rows: list[dict] = []
        region_filter = set(region_ids or [])
        zone_filter = set(zone_ids or [])
        district_filter = set(district_ids or [])
        branch_filter = set(branch_ids or [])
        format_filter = set(format_ids or [])
        status_filter = set(status_ids or [])
        optical_level_filter = set(optical_level_ids or [])

        for bucket in grouped.values():
            employee = employee_map.get(bucket["employee_id"], {})
            center_code = choose_center_code([extract_center_code(item) for item in bucket["device_ids"]])
            branch = branch_by_center.get(center_code) if center_code else None

            def rel_id(name: str) -> int | None:
                value = (branch or {}).get(name) or {}
                if isinstance(value, dict) and value.get("id"):
                    return int(value["id"])
                return None

            row = {
                "report_date": bucket["date"].isoformat(),
                "employee_id": bucket["employee_id"],
                "employee_number": employee.get("employee_number"),
                "employee_name": employee.get("name"),
                "center_code": center_code or "SIN_SUCURSAL",
                "branch": branch,
                "branch_id": int(branch["id"]) if branch and branch.get("id") else None,
                "branch_code": (branch or {}).get("branch_code"),
                "branch_name": (branch or {}).get("branch_name"),
                "region_id": rel_id("region_id"),
                "region_name": ((branch or {}).get("region_id") or {}).get("display_name"),
                "zone_id": rel_id("zone_id"),
                "zone_name": ((branch or {}).get("zone_id") or {}).get("display_name"),
                "district_id": rel_id("district_id"),
                "district_name": ((branch or {}).get("district_id") or {}).get("display_name"),
                "format_id": rel_id("format_id"),
                "format_name": ((branch or {}).get("format_id") or {}).get("display_name"),
                "status_id": rel_id("status_id"),
                "status_name": ((branch or {}).get("status_id") or {}).get("display_name"),
                "optical_level_id": rel_id("optical_level_id"),
                "optical_level": ((branch or {}).get("optical_level_id") or {}).get("display_name"),
                "first_check_in_local": bucket["first_check_in"].isoformat() if bucket["first_check_in"] else None,
                "last_check_out_local": bucket["last_check_out"].isoformat() if bucket["last_check_out"] else None,
                "worked_hours": round(bucket["worked_hours"], 2),
                "worked_hours_display": hours_to_hhmm(bucket["worked_hours"]),
            }
            if self._row_matches_filters(
                row,
                resolution_scope=resolution_scope,
                region_ids=region_filter,
                zone_ids=zone_filter,
                district_ids=district_filter,
                branch_ids=branch_filter,
                format_ids=format_filter,
                status_ids=status_filter,
                optical_level_ids=optical_level_filter,
            ):
                rows.append(row)

        rows.sort(
            key=lambda item: (
                item["report_date"],
                item["region_name"] or "",
                item["zone_name"] or "",
                item["district_name"] or "",
                item["center_code"] or "",
                item["employee_name"] or "",
            )
        )
        return rows, timezone_name
