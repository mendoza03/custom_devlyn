from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


DEVICE_ID_CENTER_RE = re.compile(r"^DEVLYN_([A-Z0-9]+)(?:_|$)")
DAY_STATE_SELECTION = [
    ("open", "Abierto"),
    ("closed", "Cerrado"),
    ("closed_auto", "Cerrado con autocierre"),
]
DAY_STATE_LABELS = dict(DAY_STATE_SELECTION)
SEGMENT_STATE_SELECTION = [
    ("open", "Abierto"),
    ("closed", "Cerrado"),
    ("closed_auto", "Cerrado con autocierre"),
]
SEGMENT_STATE_LABELS = dict(SEGMENT_STATE_SELECTION)


@dataclass(slots=True, frozen=True)
class SegmentSnapshot:
    attendance_id: int
    check_in_local: datetime
    check_out_local: datetime | None
    worked_minutes: int
    auto_closed: bool
    center_code: str | None = None
    branch_id: int | None = None

    @property
    def segment_state(self) -> str:
        if self.check_out_local is None:
            return "open"
        if self.auto_closed:
            return "closed_auto"
        return "closed"


def extract_center_code(device_id: str | None) -> str | None:
    if not device_id:
        return None
    candidate = device_id.strip().upper()
    if not candidate:
        return None
    match = DEVICE_ID_CENTER_RE.match(candidate)
    if not match:
        return None
    return match.group(1)


def choose_center_code(center_codes: list[str | None]) -> str | None:
    resolved = {code for code in center_codes if code}
    if len(resolved) == 1:
        return next(iter(resolved))
    return None


def hours_to_hhmm(hours_value: float | int | None) -> str:
    if not hours_value:
        return "00:00"
    total_minutes = max(0, round(float(hours_value) * 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def minutes_to_hhmm(minutes_value: float | int | None) -> str:
    if not minutes_value:
        return "00:00"
    total_minutes = max(0, round(float(minutes_value)))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def format_local_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_local_time(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%H:%M:%S")


def derive_segment_center_code(checkin_device_id: str | None, checkout_device_id: str | None) -> str | None:
    checkin_center = extract_center_code(checkin_device_id)
    checkout_center = extract_center_code(checkout_device_id)
    if checkin_center and checkout_center and checkin_center != checkout_center:
        return None
    return checkin_center or checkout_center


def choose_timezone(name: str | None, fallback: str = "America/Mexico_City") -> ZoneInfo:
    for candidate in [name, fallback]:
        try:
            return ZoneInfo(candidate or fallback)
        except Exception:  # noqa: BLE001
            continue
    return ZoneInfo("UTC")


def utc_bounds_for_local_dates(date_from: date, date_to: date, tz_name: str | None) -> tuple[datetime, datetime]:
    zone = choose_timezone(tz_name)
    start_local = datetime.combine(date_from, time.min, tzinfo=zone)
    end_local = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=zone)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None),
        end_local.astimezone(UTC).replace(tzinfo=None),
    )


def to_local_datetime(value: datetime | None, tz_name: str | None) -> datetime | None:
    if not value:
        return None
    zone = choose_timezone(tz_name)
    aware_value = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware_value.astimezone(zone)


def build_segment_payloads(segments: list[SegmentSnapshot]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ordered = sorted(segments, key=lambda item: (item.check_in_local, item.attendance_id))
    payloads: list[dict[str, Any]] = []
    total_gap_minutes = 0
    previous_check_out: datetime | None = None

    for sequence, segment in enumerate(ordered, start=1):
        gap_minutes: int | None = None
        gap_before_start: datetime | None = None
        gap_before_end: datetime | None = None
        if previous_check_out:
            gap_before_start = previous_check_out
            gap_before_end = segment.check_in_local
            gap_seconds = (segment.check_in_local - previous_check_out).total_seconds()
            gap_minutes = max(0, round(gap_seconds / 60))
            total_gap_minutes += gap_minutes

        payloads.append(
            {
                "sequence": sequence,
                "hr_attendance_id": segment.attendance_id,
                "check_in_local": format_local_datetime(segment.check_in_local),
                "check_out_local": format_local_datetime(segment.check_out_local),
                "worked_minutes": max(0, round(segment.worked_minutes or 0)),
                "gap_before_start_local": format_local_datetime(gap_before_start),
                "gap_before_end_local": format_local_datetime(gap_before_end),
                "gap_before_minutes": gap_minutes or 0,
                "segment_state": segment.segment_state,
                "center_code": segment.center_code or "SIN_SUCURSAL",
                "branch_id": segment.branch_id or False,
            }
        )
        previous_check_out = segment.check_out_local

    has_open_segment = any(item["segment_state"] == "open" for item in payloads)
    has_auto_close = any(item["segment_state"] == "closed_auto" for item in payloads)
    day_state = "open" if has_open_segment else "closed_auto" if has_auto_close else "closed"
    return payloads, {
        "segment_count": len(payloads),
        "intermittence_count": max(len(payloads) - 1, 0),
        "total_gap_minutes": total_gap_minutes,
        "day_state": day_state,
        "has_auto_close": has_auto_close,
    }
