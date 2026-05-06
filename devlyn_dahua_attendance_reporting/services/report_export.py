from __future__ import annotations

import base64
import io
from datetime import datetime

import xlsxwriter
from odoo import models

from .report_utils import (
    SEGMENT_STATE_LABELS,
    build_segment_payloads,
    choose_center_code,
    extract_center_code,
    format_local_time,
    hours_to_hhmm,
    minutes_to_hhmm,
    to_local_datetime,
    utc_bounds_for_local_dates,
)


class DevlynAttendanceBranchReportService:
    HEADERS = [
        "Fecha",
        "IdEmpleado",
        "NombreCompleto",
        "IdCentro",
        "Sucursal",
        "NombreSucursal",
        "Nivel Óptica Ventas",
        "Formato",
        "Estatus",
        "Región",
        "Zona",
        "Distrito",
        "Hora Entrada",
        "Hora Salida",
        "Tiempo efectivo",
    ]
    INTERMITTENCE_HEADERS = [
        "Intermitencias",
        "Tiempo intermitente",
        "Estado del día",
    ]
    DETAIL_HEADERS = [
        "Fecha",
        "IdEmpleado",
        "NombreCompleto",
        "Tramo #",
        "Hora Entrada",
        "Hora Salida",
        "Tiempo tramo",
        "Inicio intermitencia previa",
        "Fin intermitencia previa",
        "Tiempo intermitencia previa",
        "Estado tramo",
        "IdCentro",
        "Sucursal",
        "NombreSucursal",
    ]

    def __init__(self, env):
        self.env = env

    def get_timezone_name(self) -> str:
        config = self.env["hr.biometric.sync.config"].search([], limit=1)
        return config.timezone_name or "America/Mexico_City"

    def _journey_service(self):
        return self.env["devlyn.attendance.journey.service"]

    def _build_domain(self, source, tz_name: str):
        start_utc, end_utc = utc_bounds_for_local_dates(source.date_from, source.date_to, tz_name)
        domain = [
            ("biometric_source", "=", "biometric_v1"),
            ("check_in", ">=", start_utc),
            ("check_in", "<", end_utc),
        ]
        if source.employee_ids:
            domain.append(("employee_id", "in", source.employee_ids.ids))
        return domain

    def _derive_branch(self, device_ids: list[str | None], branch_by_center: dict[str, object]):
        center_codes = [extract_center_code(device_id) for device_id in device_ids]
        center_code = choose_center_code(center_codes)
        if not center_code:
            return None
        return branch_by_center.get(center_code)

    def _row_matches_filters(self, row: dict, source) -> bool:
        branch = row["branch"]
        if source.resolution_scope == "mapped_only" and not branch:
            return False
        if source.resolution_scope == "sin_sucursal_only" and branch:
            return False

        filter_pairs = [
            ("region_ids", "region_id"),
            ("zone_ids", "zone_id"),
            ("district_ids", "district_id"),
            ("branch_ids", "branch_id"),
            ("format_ids", "format_id"),
            ("status_ids", "status_id"),
            ("optical_level_ids", "optical_level_id"),
        ]
        for source_field, row_field in filter_pairs:
            selected = source[source_field]
            if not selected:
                continue
            if not branch:
                return False
            if row[row_field] not in selected.ids:
                return False
        return True

    def _build_journey_map(self, keys: set[tuple[int, object]]) -> dict[tuple[int, object], object]:
        if not keys:
            return {}
        employee_ids = sorted({employee_id for employee_id, _ in keys})
        local_dates = sorted({local_date for _, local_date in keys})
        journeys = self.env["devlyn.attendance.journey"].search(
            [("employee_id", "in", employee_ids), ("local_date", "in", local_dates)]
        )
        return {(journey.employee_id.id, journey.local_date): journey for journey in journeys}

    def _fallback_journey_summary(self, bucket: dict) -> dict:
        segment_snapshots = bucket.get("segment_snapshots", [])
        if not segment_snapshots:
            return {
                "segment_count": len(bucket["attendance_ids"]),
                "intermittence_count": max(len(bucket["attendance_ids"]) - 1, 0),
                "total_gap_minutes": 0,
                "day_state": "open" if bucket["last_check_out"] is None else "closed",
                "has_auto_close": False,
            }
        _payloads, summary = build_segment_payloads(segment_snapshots)
        return summary

    def build_rows(self, source) -> list[dict]:
        tz_name = self.get_timezone_name()
        journey_service = self._journey_service()
        attendances = self.env["hr.attendance"].search(
            self._build_domain(source, tz_name),
            order="employee_id, check_in, id",
        )
        branches = self.env["devlyn.catalog.branch"].search([])
        branch_by_center = {record.center_code: record for record in branches}

        grouped: dict[tuple[int, object], dict] = {}
        for attendance in attendances:
            local_check_in = to_local_datetime(attendance.check_in, tz_name)
            if not local_check_in:
                continue
            local_check_out = to_local_datetime(attendance.check_out, tz_name)
            key = (attendance.employee_id.id, local_check_in.date())
            bucket = grouped.setdefault(
                key,
                {
                    "attendance_ids": [],
                    "employee": attendance.employee_id,
                    "date": local_check_in.date(),
                    "first_check_in": local_check_in,
                    "last_check_out": local_check_out,
                    "worked_hours": 0.0,
                    "device_ids": [],
                    "segment_snapshots": [],
                },
            )
            bucket["attendance_ids"].append(attendance.id)
            if local_check_in < bucket["first_check_in"]:
                bucket["first_check_in"] = local_check_in
            if local_check_out and (
                bucket["last_check_out"] is None or local_check_out > bucket["last_check_out"]
            ):
                bucket["last_check_out"] = local_check_out
            bucket["worked_hours"] += attendance.worked_hours or 0.0
            bucket["device_ids"].append(attendance.biometric_checkin_event_id.device_id_resolved or None)
            bucket["device_ids"].append(attendance.biometric_checkout_event_id.device_id_resolved or None)
            segment_snapshot = journey_service.build_segment_snapshot(attendance, tz_name, branch_by_center)
            if segment_snapshot:
                bucket["segment_snapshots"].append(segment_snapshot)

        journey_by_key = self._build_journey_map(set(grouped))
        rows: list[dict] = []
        for key, bucket in grouped.items():
            branch = self._derive_branch(bucket["device_ids"], branch_by_center)
            journey = journey_by_key.get(key)
            fallback_summary = self._fallback_journey_summary(bucket)
            intermittence_count = journey.intermittence_count if journey else fallback_summary["intermittence_count"]
            total_gap_minutes = journey.total_gap_minutes if journey else fallback_summary["total_gap_minutes"]
            day_state = journey.day_state if journey else fallback_summary["day_state"]
            row = {
                "date": bucket["date"],
                "employee_id": bucket["employee"].id,
                "employee_number": bucket["employee"].employee_number or "",
                "employee_name": bucket["employee"].name or "",
                "center_code": branch.center_code if branch else "SIN_SUCURSAL",
                "branch_code": branch.branch_code if branch else "",
                "branch_name": branch.branch_name if branch else "",
                "optical_level": branch.optical_level_id.code if branch else "",
                "format_name": branch.format_id.name if branch else "",
                "status_name": branch.status_id.name if branch else "",
                "region_name": branch.region_id.name if branch else "",
                "zone_name": branch.zone_id.name if branch else "",
                "district_name": branch.district_id.name if branch else "",
                "first_check_in": bucket["first_check_in"],
                "last_check_out": bucket["last_check_out"],
                "worked_hours": bucket["worked_hours"],
                "branch": branch,
                "region_id": branch.region_id.id if branch else False,
                "zone_id": branch.zone_id.id if branch else False,
                "district_id": branch.district_id.id if branch else False,
                "branch_id": branch.id if branch else False,
                "format_id": branch.format_id.id if branch else False,
                "status_id": branch.status_id.id if branch else False,
                "optical_level_id": branch.optical_level_id.id if branch else False,
                "intermittence_count": intermittence_count,
                "total_gap_minutes": total_gap_minutes,
                "day_state": day_state,
            }
            if self._row_matches_filters(row, source):
                rows.append(row)

        rows.sort(
            key=lambda item: (
                item["date"],
                item["region_name"],
                item["zone_name"],
                item["district_name"],
                item["center_code"],
                item["employee_name"],
            )
        )
        return rows

    def build_viewer_payload(self, source) -> tuple[list[dict], dict[str, int]]:
        rows = self.build_rows(source)
        line_values = [self._row_to_viewer_line_values(row) for row in rows]
        mapped_rows = sum(1 for row in rows if row["branch"])
        summary = {
            "total_rows": len(rows),
            "mapped_rows": mapped_rows,
            "unmapped_rows": len(rows) - mapped_rows,
        }
        return line_values, summary

    def _row_to_viewer_line_values(self, row: dict) -> dict:
        employee_number = row["employee_number"]
        if employee_number not in ("", False, None):
            employee_number = str(employee_number)
        else:
            employee_number = ""

        return {
            "report_date": row["date"],
            "employee_id": row["employee_id"],
            "employee_number": employee_number,
            "employee_name": row["employee_name"],
            "center_code": row["center_code"],
            "branch_id": row["branch_id"] or False,
            "branch_code": row["branch_code"],
            "branch_name": row["branch_name"],
            "optical_level_id": row["optical_level_id"] or False,
            "optical_level_display": row["optical_level"],
            "format_id": row["format_id"] or False,
            "status_id": row["status_id"] or False,
            "region_id": row["region_id"] or False,
            "zone_id": row["zone_id"] or False,
            "district_id": row["district_id"] or False,
            "region_name": row["region_name"],
            "zone_name": row["zone_name"],
            "district_name": row["district_name"],
            "first_check_in_display": (
                row["first_check_in"].strftime("%H:%M:%S") if row["first_check_in"] else ""
            ),
            "last_check_out_display": (
                row["last_check_out"].strftime("%H:%M:%S") if row["last_check_out"] else ""
            ),
            "worked_hours": row["worked_hours"],
            "worked_hours_display": hours_to_hhmm(row["worked_hours"]),
            "intermittence_count": row["intermittence_count"],
            "total_gap_minutes": row["total_gap_minutes"],
            "total_gap_display": minutes_to_hhmm(row["total_gap_minutes"]),
            "day_state": row["day_state"],
            "is_unmapped": not bool(row["branch"]),
        }

    def build_xlsx(self, rows: list[dict], include_intermitencias: bool = False) -> bytes:
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Asistencias Sucursal")

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        text_fmt = workbook.add_format({"border": 1})
        date_fmt = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd"})

        headers = list(self.HEADERS)
        widths = [12, 14, 32, 14, 14, 32, 16, 14, 14, 20, 20, 20, 14, 14, 14]
        if include_intermitencias:
            headers.extend(self.INTERMITTENCE_HEADERS)
            widths.extend([14, 18, 20])

        for idx, width in enumerate(widths):
            sheet.set_column(idx, idx, width)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(rows), 1), len(headers) - 1)

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)

        journey_service = self._journey_service()
        for row_idx, row in enumerate(rows, start=1):
            sheet.write_datetime(
                row_idx,
                0,
                datetime.combine(row["date"], datetime.min.time()),
                date_fmt,
            )
            sheet.write(row_idx, 1, row["employee_number"], text_fmt)
            sheet.write(row_idx, 2, row["employee_name"], text_fmt)
            sheet.write(row_idx, 3, row["center_code"], text_fmt)
            sheet.write(row_idx, 4, row["branch_code"], text_fmt)
            sheet.write(row_idx, 5, row["branch_name"], text_fmt)
            sheet.write(row_idx, 6, row["optical_level"], text_fmt)
            sheet.write(row_idx, 7, row["format_name"], text_fmt)
            sheet.write(row_idx, 8, row["status_name"], text_fmt)
            sheet.write(row_idx, 9, row["region_name"], text_fmt)
            sheet.write(row_idx, 10, row["zone_name"], text_fmt)
            sheet.write(row_idx, 11, row["district_name"], text_fmt)
            sheet.write(
                row_idx,
                12,
                row["first_check_in"].strftime("%H:%M:%S") if row["first_check_in"] else "",
                text_fmt,
            )
            sheet.write(
                row_idx,
                13,
                row["last_check_out"].strftime("%H:%M:%S") if row["last_check_out"] else "",
                text_fmt,
            )
            sheet.write(row_idx, 14, hours_to_hhmm(row["worked_hours"]), text_fmt)
            if include_intermitencias:
                sheet.write(row_idx, 15, row["intermittence_count"], text_fmt)
                sheet.write(row_idx, 16, minutes_to_hhmm(row["total_gap_minutes"]), text_fmt)
                sheet.write(row_idx, 17, journey_service.day_state_label(row["day_state"]), text_fmt)

        workbook.close()
        return output.getvalue()

    def export_payload(self, source) -> tuple[str, str]:
        rows = self.build_rows(source)
        include_intermitencias = bool(getattr(source, "show_intermitencias", False))
        content = self.build_xlsx(rows, include_intermitencias=include_intermitencias)
        file_name = f"asistencias_por_sucursal_{source.date_from}_{source.date_to}.xlsx"
        return file_name, base64.b64encode(content).decode()

    def _build_segment_domain(self, source) -> list:
        domain = [
            ("local_date", ">=", source.date_from),
            ("local_date", "<=", source.date_to),
        ]
        if source.employee_ids:
            domain.append(("employee_id", "in", source.employee_ids.ids))
        if source.resolution_scope == "mapped_only":
            domain.append(("branch_id", "!=", False))
        elif source.resolution_scope == "sin_sucursal_only":
            domain.append(("branch_id", "=", False))
        if source.region_ids:
            domain.append(("region_id", "in", source.region_ids.ids))
        if source.zone_ids:
            domain.append(("zone_id", "in", source.zone_ids.ids))
        if source.district_ids:
            domain.append(("district_id", "in", source.district_ids.ids))
        if source.branch_ids:
            domain.append(("branch_id", "in", source.branch_ids.ids))
        if source.format_ids:
            domain.append(("format_id", "in", source.format_ids.ids))
        if source.status_ids:
            domain.append(("status_id", "in", source.status_ids.ids))
        if source.optical_level_ids:
            domain.append(("optical_level_id", "in", source.optical_level_ids.ids))
        return domain

    def build_segment_rows(self, source) -> list[dict]:
        segments = self.env["devlyn.attendance.journey.segment"].search(
            self._build_segment_domain(source),
            order="local_date desc, employee_id, sequence, id",
        )
        rows: list[dict] = []
        for segment in segments:
            employee = segment.employee_id
            rows.append(
                {
                    "report_date": segment.local_date,
                    "employee_id": employee.id if employee else False,
                    "employee_number": str(employee.employee_number or "") if employee else "",
                    "employee_name": employee.name or "" if employee else "",
                    "segment_sequence": segment.sequence,
                    "check_in_display": segment.check_in_local[-8:] if segment.check_in_local else "",
                    "check_out_display": segment.check_out_local[-8:] if segment.check_out_local else "",
                    "worked_minutes": segment.worked_minutes,
                    "worked_minutes_display": minutes_to_hhmm(segment.worked_minutes),
                    "gap_before_start_display": segment.gap_before_start_local[-8:] if segment.gap_before_start_local else "",
                    "gap_before_end_display": segment.gap_before_end_local[-8:] if segment.gap_before_end_local else "",
                    "gap_before_minutes": segment.gap_before_minutes,
                    "gap_before_display": minutes_to_hhmm(segment.gap_before_minutes),
                    "segment_state": segment.segment_state,
                    "center_code": segment.center_code or "SIN_SUCURSAL",
                    "branch_id": segment.branch_id.id if segment.branch_id else False,
                    "branch_code": segment.branch_code or "",
                    "branch_name": segment.branch_name or "",
                }
            )
        return rows

    def build_segment_viewer_payload(self, source) -> tuple[list[dict], dict[str, int]]:
        rows = self.build_segment_rows(source)
        line_values = [self._segment_row_to_viewer_line_values(row) for row in rows]
        return line_values, {"total_rows": len(rows)}

    def _segment_row_to_viewer_line_values(self, row: dict) -> dict:
        return {
            "report_date": row["report_date"],
            "employee_id": row["employee_id"] or False,
            "employee_number": row["employee_number"],
            "employee_name": row["employee_name"],
            "segment_sequence": row["segment_sequence"],
            "first_check_in_display": row["check_in_display"],
            "last_check_out_display": row["check_out_display"],
            "worked_minutes": row["worked_minutes"],
            "worked_minutes_display": row["worked_minutes_display"],
            "gap_before_start_display": row["gap_before_start_display"],
            "gap_before_end_display": row["gap_before_end_display"],
            "gap_before_minutes": row["gap_before_minutes"],
            "gap_before_display": row["gap_before_display"],
            "segment_state": row["segment_state"],
            "center_code": row["center_code"],
            "branch_id": row["branch_id"] or False,
            "branch_code": row["branch_code"],
            "branch_name": row["branch_name"],
        }

    def build_segment_xlsx(self, rows: list[dict]) -> bytes:
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Detalle Intermitencias")

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        text_fmt = workbook.add_format({"border": 1})
        date_fmt = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd"})

        widths = [12, 14, 32, 10, 14, 14, 14, 18, 18, 18, 18, 14, 14, 32]
        for idx, width in enumerate(widths):
            sheet.set_column(idx, idx, width)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(rows), 1), len(self.DETAIL_HEADERS) - 1)

        for col, header in enumerate(self.DETAIL_HEADERS):
            sheet.write(0, col, header, header_fmt)

        for row_idx, row in enumerate(rows, start=1):
            sheet.write_datetime(
                row_idx,
                0,
                datetime.combine(row["report_date"], datetime.min.time()),
                date_fmt,
            )
            sheet.write(row_idx, 1, row["employee_number"], text_fmt)
            sheet.write(row_idx, 2, row["employee_name"], text_fmt)
            sheet.write(row_idx, 3, row["segment_sequence"], text_fmt)
            sheet.write(row_idx, 4, row["check_in_display"], text_fmt)
            sheet.write(row_idx, 5, row["check_out_display"], text_fmt)
            sheet.write(row_idx, 6, row["worked_minutes_display"], text_fmt)
            sheet.write(row_idx, 7, row["gap_before_start_display"], text_fmt)
            sheet.write(row_idx, 8, row["gap_before_end_display"], text_fmt)
            sheet.write(row_idx, 9, row["gap_before_display"], text_fmt)
            sheet.write(row_idx, 10, SEGMENT_STATE_LABELS.get(row["segment_state"], ""), text_fmt)
            sheet.write(row_idx, 11, row["center_code"], text_fmt)
            sheet.write(row_idx, 12, row["branch_code"], text_fmt)
            sheet.write(row_idx, 13, row["branch_name"], text_fmt)

        workbook.close()
        return output.getvalue()

    def export_segment_payload(self, source) -> tuple[str, str]:
        rows = self.build_segment_rows(source)
        content = self.build_segment_xlsx(rows)
        file_name = f"detalle_intermitencias_{source.date_from}_{source.date_to}.xlsx"
        return file_name, base64.b64encode(content).decode()


class DevlynAttendanceBranchReportServiceModel(models.AbstractModel):
    _name = "devlyn.attendance.branch.report.service"
    _description = "Devlyn Attendance Branch Report Service"

    def get_timezone_name(self):
        return DevlynAttendanceBranchReportService(self.env).get_timezone_name()

    def build_rows(self, source):
        return DevlynAttendanceBranchReportService(self.env).build_rows(source)

    def build_viewer_payload(self, source):
        return DevlynAttendanceBranchReportService(self.env).build_viewer_payload(source)

    def export_payload(self, source):
        return DevlynAttendanceBranchReportService(self.env).export_payload(source)

    def build_segment_rows(self, source):
        return DevlynAttendanceBranchReportService(self.env).build_segment_rows(source)

    def build_segment_viewer_payload(self, source):
        return DevlynAttendanceBranchReportService(self.env).build_segment_viewer_payload(source)

    def export_segment_payload(self, source):
        return DevlynAttendanceBranchReportService(self.env).export_segment_payload(source)
