from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from starlette.testclient import TestClient

from odoo_mcp.app import create_app
from odoo_mcp.config import Settings


class TimezoneDummyPg:
    def healthcheck(self) -> dict[str, object]:
        return {"db": "biometric_ingest", "usr": "mcp_readonly", "ok": 1}

    def close(self) -> None:
        return None


class TimezoneBranchReport:
    def build_rows(self, **_: object):
        return [], "America/Mexico_City"


class TimezoneOdoo:
    def __init__(self):
        self._employee = {
            "id": 12926,
            "name": "CHAVEZ FIGUEROA LEONARDO",
            "employee_number": 34054,
            "active": True,
        }
        self._attendance = [
            {
                "id": 9002,
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "check_in": "2026-04-13 04:30:00",
                "check_out": "2026-04-13 05:59:59",
                "worked_hours": 1.5,
                "biometric_source": "biometric_v1",
            },
            {
                "id": 9001,
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "check_in": "2026-04-01 18:22:46",
                "check_out": "2026-04-02 03:05:52",
                "worked_hours": 8.72,
                "biometric_source": "biometric_v1",
            },
        ]
        self._biometric_events = [
            {
                "id": 7004,
                "event_occurred_at_utc": "2026-04-13 05:59:59",
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "user_id_on_device": "34054",
                "device_id_resolved": "DEVLYN_100_TEST",
                "sync_status": "check_out_written",
                "attendance_action": "check_out",
            },
            {
                "id": 7003,
                "event_occurred_at_utc": "2026-04-13 04:30:00",
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "user_id_on_device": "34054",
                "device_id_resolved": "DEVLYN_100_TEST",
                "sync_status": "check_in_created",
                "attendance_action": "check_in",
            },
            {
                "id": 7002,
                "event_occurred_at_utc": "2026-04-02 03:05:52",
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "user_id_on_device": "34054",
                "device_id_resolved": "DEVLYN_100_TEST",
                "sync_status": "check_out_written",
                "attendance_action": "check_out",
            },
            {
                "id": 7001,
                "event_occurred_at_utc": "2026-04-01 18:22:46",
                "employee_id": {"id": 12926, "display_name": "CHAVEZ FIGUEROA LEONARDO"},
                "user_id_on_device": "34054",
                "device_id_resolved": "DEVLYN_100_TEST",
                "sync_status": "check_in_created",
                "attendance_action": "check_in",
            },
        ]

    def healthcheck(self) -> dict[str, object]:
        return {"server_version": "19.0", "authenticated_uid": 999}

    def close(self) -> None:
        return None

    def get_timezone_name(self, fallback_timezone: str) -> str:
        return "America/Mexico_City"

    def existing_fields(self, model: str, candidates: list[str]) -> list[str]:
        known = set(self._model_fields(model))
        return [field for field in candidates if field in known]

    def search_count(self, model: str, domain: list[object]) -> int:
        if model == "hr.attendance":
            return len(self._filter_rows(self._attendance, domain, timestamp_field="check_in"))
        if model == "hr.biometric.event":
            return len(self._filter_rows(self._biometric_events, domain, timestamp_field="event_occurred_at_utc"))
        return 0

    def search_read(
        self,
        model: str,
        domain: list[object],
        *,
        fields: list[str],
        limit: int,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, object]]:
        if model == "hr.attendance":
            rows = self._filter_rows(self._attendance, domain, timestamp_field="check_in")
        elif model == "hr.biometric.event":
            rows = self._filter_rows(self._biometric_events, domain, timestamp_field="event_occurred_at_utc")
        else:
            rows = []

        if order == "check_in desc, id desc":
            rows = sorted(rows, key=lambda row: (row["check_in"], row["id"]), reverse=True)
        elif order == "event_occurred_at_utc desc, id desc":
            rows = sorted(rows, key=lambda row: (row["event_occurred_at_utc"], row["id"]), reverse=True)

        window = rows[offset : offset + limit]
        return [{field: row.get(field) for field in fields if field in row} for row in window]

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict[str, object]]:
        id_set = {int(item) for item in ids}
        if model == "hr.attendance":
            rows = [row for row in self._attendance if int(row["id"]) in id_set]
        elif model == "hr.biometric.event":
            rows = [row for row in self._biometric_events if int(row["id"]) in id_set]
        else:
            rows = []
        return [{field: row.get(field) for field in fields if field in row} for row in rows]

    def _model_fields(self, model: str) -> dict[str, dict[str, object]]:
        if model == "hr.attendance":
            return {
                "id": {"type": "integer"},
                "employee_id": {"type": "many2one"},
                "check_in": {"type": "datetime"},
                "check_out": {"type": "datetime"},
                "worked_hours": {"type": "float"},
                "biometric_source": {"type": "char"},
            }
        if model == "hr.biometric.event":
            return {
                "id": {"type": "integer"},
                "event_occurred_at_utc": {"type": "datetime"},
                "employee_id": {"type": "many2one"},
                "user_id_on_device": {"type": "char"},
                "device_id_resolved": {"type": "char"},
                "sync_status": {"type": "char"},
                "attendance_action": {"type": "char"},
            }
        return {}

    def _filter_rows(
        self,
        rows: list[dict[str, object]],
        domain: list[object],
        *,
        timestamp_field: str,
    ) -> list[dict[str, object]]:
        filtered = list(rows)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field_name, operator, value = condition
            if field_name == timestamp_field and operator in {">=", "<", "<="}:
                filtered = [
                    row
                    for row in filtered
                    if self._compare_timestamp(str(row.get(timestamp_field) or ""), operator, str(value))
                ]
            elif field_name == "employee_id" and operator == "in":
                allowed = {int(item) for item in value}
                filtered = [
                    row
                    for row in filtered
                    if int(((row.get("employee_id") or {}).get("id")) or 0) in allowed
                ]
        return filtered

    def _compare_timestamp(self, current: str, operator: str, expected: str) -> bool:
        if operator == ">=":
            return current >= expected
        if operator == "<":
            return current < expected
        if operator == "<=":
            return current <= expected
        return False


@dataclass
class TimezoneRuntime:
    settings: Settings
    odoo: TimezoneOdoo
    biometric_ingest: TimezoneDummyPg
    branch_report: TimezoneBranchReport

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_timezone_client() -> TestClient:
    settings = Settings(
        app_name="Devlyn Test MCP",
        app_version="1.0.0-test",
        public_base_url="https://mcp.example.test",
        mcp_mount_path="/mcp",
        host="127.0.0.1",
        port=8071,
        mcp_api_key="top-secret",
        odoo_url="https://erp.example.test",
        odoo_db="devlyn_com",
        odoo_login="mcp.readonly",
        odoo_api_key="odoo-api-key",
        odoo_locale="es_MX",
        odoo_timeout_seconds=15,
        biometric_pg_dsn="postgresql://mcp_readonly:secret@127.0.0.1/biometric_ingest",
        biometric_pg_connect_timeout_seconds=5,
        biometric_pg_statement_timeout_ms=5000,
        default_limit=50,
        max_limit=200,
        default_window_days=7,
        cache_ttl_seconds=300,
        default_timezone="America/Mexico_City",
        log_level="INFO",
    )
    runtime = TimezoneRuntime(
        settings=settings,
        odoo=TimezoneOdoo(),
        biometric_ingest=TimezoneDummyPg(),
        branch_report=TimezoneBranchReport(),
    )
    return TestClient(create_app(settings=settings, runtime=runtime))


def _call_tool(client: TestClient, name: str, arguments: dict | None = None) -> dict:
    response = client.post(
        "/mcp",
        headers={
            "x-api-key": "top-secret",
            "accept": "application/json",
            "mcp-protocol-version": "2025-06-18",
            "host": "mcp.example.test",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}},
    )
    assert response.status_code == 200
    payload = response.json()
    return json.loads(payload["result"]["content"][0]["text"])


def test_search_attendance_records_returns_local_mexico_city_time():
    with build_timezone_client() as client:
        payload = _call_tool(
            client,
            "search_attendance_records",
            {"date_from": "2026-04-01", "date_to": "2026-04-13", "employee_ids": [12926]},
        )

    assert payload["summary"]["timezone_name"] == "America/Mexico_City"
    assert payload["summary"]["timestamp_format"] == "iso8601_offset"
    assert {
        (item["check_in"], item["check_out"])
        for item in payload["items"]
    } == {
        ("2026-04-01T12:22:46-06:00", "2026-04-01T21:05:52-06:00"),
        ("2026-04-12T22:30:00-06:00", "2026-04-12T23:59:59-06:00"),
    }


def test_search_hr_biometric_events_keeps_explicit_utc_timestamps():
    with build_timezone_client() as client:
        payload = _call_tool(
            client,
            "search_hr_biometric_events",
            {"date_from": "2026-04-01", "date_to": "2026-04-13", "employee_ids": [12926]},
        )

    assert payload["summary"]["timezone_name"] == "UTC"
    assert payload["summary"]["timestamp_format"] == "iso8601_offset"
    assert [item["event_occurred_at_utc"] for item in payload["items"]] == [
        "2026-04-13T05:59:59+00:00",
        "2026-04-13T04:30:00+00:00",
        "2026-04-02T03:05:52+00:00",
        "2026-04-01T18:22:46+00:00",
    ]


def test_attendance_local_times_and_biometric_utc_times_are_same_instants():
    with build_timezone_client() as client:
        attendance = _call_tool(
            client,
            "search_attendance_records",
            {"date_from": "2026-04-01", "date_to": "2026-04-13", "employee_ids": [12926]},
        )
        events = _call_tool(
            client,
            "search_hr_biometric_events",
            {"date_from": "2026-04-01", "date_to": "2026-04-13", "employee_ids": [12926]},
        )

    event_instants = {
        datetime.fromisoformat(item["event_occurred_at_utc"]).astimezone(UTC).isoformat()
        for item in events["items"]
    }
    attendance_instants = {
        datetime.fromisoformat(item[field]).astimezone(UTC).isoformat()
        for item in attendance["items"]
        for field in ("check_in", "check_out")
        if item.get(field)
    }

    assert attendance_instants <= event_instants
