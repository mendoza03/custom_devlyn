from __future__ import annotations

import json
from dataclasses import dataclass

from starlette.testclient import TestClient

from odoo_mcp.app import create_app
from odoo_mcp.config import Settings
from odoo_mcp.server import build_controlled_list_envelope


class VolumeDummyPg:
    def healthcheck(self) -> dict[str, object]:
        return {"db": "biometric_ingest", "usr": "mcp_readonly", "ok": 1}

    def close(self) -> None:
        return None


class VolumeBranchReport:
    def build_rows(self, **_: object):
        return [], "UTC"


class VolumeOdoo:
    def __init__(self):
        self._employees = [
            {
                "id": index,
                "name": f"Empleado {index}",
                "employee_number": 1000 + index,
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "parent_id": {"id": 2000 + index, "display_name": f"Manager {index}"},
                "user_id": False,
                "active": True,
            }
            for index in range(1, 31)
        ]
        self._attendance_summary = [
            {
                "id": index,
                "summary_date": "2026-04-12",
                "employee_id": {"id": index, "display_name": f"Empleado {index}"},
                "user_id": False,
                "login": f"user{index}",
                "first_check_in": f"2026-04-12T08:{index % 60:02d}:00",
                "last_check_out": f"2026-04-12T18:{index % 60:02d}:00",
                "total_worked_hours": float(index),
                "segments": 2,
                "open_segments": 0 if index % 2 == 0 else 1,
            }
            for index in range(1, 21)
        ]
        self._users = [
            {"id": 16, "name": "Ivan", "login": "ivan@example.test", "active": True},
            {"id": 12, "name": "Adriana Mendoza", "login": "adriana@example.test", "active": True},
            {"id": 2, "name": "Administrator", "login": "admin@example.test", "active": True},
        ]
        self._projects = [
            {
                "id": 3,
                "name": "Biométricos",
                "display_name": "Biométricos",
                "user_id": {"id": 12, "display_name": "Adriana Mendoza"},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
            },
            {
                "id": 2,
                "name": "Otro Proyecto",
                "display_name": "Otro Proyecto",
                "user_id": {"id": 16, "display_name": "Ivan"},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
            },
        ]
        self._task_stages = [
            {"id": 86, "name": "Configuración y Pruebas", "display_name": "Configuración y Pruebas", "fold": False, "sequence": 1, "active": True},
            {"id": 70, "name": "Pendiente", "display_name": "Pendiente", "fold": False, "sequence": 2, "active": True},
            {"id": 77, "name": "Hecha", "display_name": "Hecha", "fold": True, "sequence": 6, "active": True},
        ]
        self._tasks = [
            {
                "id": 19,
                "name": "Configuraciones de Correo",
                "display_name": "Configuraciones de Correo",
                "project_id": {"id": 3, "display_name": "Biométricos"},
                "user_ids": [16],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 86, "display_name": "Configuración y Pruebas"},
            },
            {
                "id": 15,
                "name": "Validación de Primera Carga",
                "display_name": "Validación de Primera Carga",
                "project_id": {"id": 3, "display_name": "Biométricos"},
                "user_ids": [12],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 86, "display_name": "Configuración y Pruebas"},
            },
            {
                "id": 14,
                "name": "Tarea Fuera de Proyecto",
                "display_name": "Tarea Fuera de Proyecto",
                "project_id": {"id": 2, "display_name": "Otro"},
                "user_ids": [16],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 70, "display_name": "Pendiente"},
            },
            {
                "id": 1,
                "name": "Tarea con m2m roto",
                "display_name": "Tarea con m2m roto",
                "project_id": {"id": 2, "display_name": "Otro Proyecto"},
                "user_ids": {"id": 2, "display_name": 10},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 77, "display_name": "Hecha"},
            },
        ]

    def healthcheck(self) -> dict[str, object]:
        return {"server_version": "19.0", "authenticated_uid": 999}

    def close(self) -> None:
        return None

    def get_timezone_name(self, fallback_timezone: str) -> str:
        return fallback_timezone

    def fields_get(self, model: str) -> dict[str, object]:
        return dict(self._model_fields(model))

    def existing_fields(self, model: str, candidates: list[str]) -> list[str]:
        known = set(self._model_fields(model))
        return [field for field in candidates if field in known]

    def search_count(self, model: str, domain: list[object]) -> int:
        if model == "hr.employee":
            return len(self._employees)
        if model == "biometric.attendance.summary":
            return len(self._attendance_summary)
        if model == "project.task":
            return len(self._filter_tasks(domain))
        if model == "res.users":
            return len(self._users)
        if model == "project.project":
            return len(self._filter_projects(domain))
        if model == "project.task.type":
            return len(self._task_stages)
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
        if model == "hr.employee":
            data = self._employees
        elif model == "biometric.attendance.summary":
            data = self._attendance_summary
        elif model == "project.task":
            data = self._filter_tasks(domain)
        elif model == "res.users":
            data = self._users
        elif model == "project.project":
            data = self._filter_projects(domain)
        elif model == "project.task.type":
            data = self._task_stages
        else:
            data = []
        rows = data[offset : offset + limit]
        return [{field: row.get(field) for field in fields if field in row} for row in rows]

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict[str, object]]:
        if model == "res.users":
            data = self._users
        elif model == "project.task":
            data = self._tasks
        elif model == "project.project":
            data = self._projects
        elif model == "project.task.type":
            data = self._task_stages
        elif model == "hr.employee":
            data = self._employees
        elif model == "biometric.attendance.summary":
            data = self._attendance_summary
        else:
            data = []
        id_set = {int(item) for item in ids}
        rows = [row for row in data if int(row.get("id", 0)) in id_set]
        return [{field: row.get(field) for field in fields if field in row} for row in rows]

    def _model_fields(self, model: str) -> dict[str, dict[str, object]]:
        if model == "hr.employee":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "employee_number": {"type": "integer"},
                "company_id": {"type": "many2one"},
                "parent_id": {"type": "many2one"},
                "user_id": {"type": "many2one"},
                "active": {"type": "boolean"},
            }
        if model == "biometric.attendance.summary":
            return {
                "id": {"type": "integer"},
                "summary_date": {"type": "date"},
                "employee_id": {"type": "many2one"},
                "user_id": {"type": "many2one"},
                "login": {"type": "char"},
                "first_check_in": {"type": "datetime"},
                "last_check_out": {"type": "datetime"},
                "total_worked_hours": {"type": "float"},
                "segments": {"type": "integer"},
                "open_segments": {"type": "integer"},
            }
        if model == "project.task":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "project_id": {"type": "many2one"},
                "user_ids": {"type": "many2many"},
                "company_id": {"type": "many2one"},
                "active": {"type": "boolean"},
                "stage_id": {"type": "many2one"},
            }
        if model == "res.users":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "login": {"type": "char"},
                "active": {"type": "boolean"},
            }
        if model == "project.project":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "user_id": {"type": "many2one"},
                "company_id": {"type": "many2one"},
                "active": {"type": "boolean"},
            }
        if model == "project.task.type":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "fold": {"type": "boolean"},
                "sequence": {"type": "integer"},
                "active": {"type": "boolean"},
            }
        return {}

    def _filter_tasks(self, domain: list[object]) -> list[dict[str, object]]:
        rows = list(self._tasks)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field, operator, value = condition
            if field == "active" and operator == "=":
                rows = [row for row in rows if bool(row.get("active")) is bool(value)]
            elif field == "project_id" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [row for row in rows if int((row.get("project_id") or {}).get("id", 0)) in allowed]
            elif field == "stage_id" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [row for row in rows if int((row.get("stage_id") or {}).get("id", 0)) in allowed]
            elif field == "user_ids" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [
                    row
                    for row in rows
                    if any(int(user_id) in allowed for user_id in ([row["user_ids"]["id"]] if isinstance(row.get("user_ids"), dict) else (row.get("user_ids") or [])))
                ]
        return rows

    def _filter_projects(self, domain: list[object]) -> list[dict[str, object]]:
        rows = list(self._projects)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field, operator, value = condition
            if field == "active" and operator == "=":
                rows = [row for row in rows if bool(row.get("active")) is bool(value)]
        return rows


@dataclass
class VolumeRuntime:
    settings: Settings
    odoo: VolumeOdoo
    biometric_ingest: VolumeDummyPg
    branch_report: VolumeBranchReport

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_volume_test_client() -> TestClient:
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
    runtime = VolumeRuntime(
        settings=settings,
        odoo=VolumeOdoo(),
        biometric_ingest=VolumeDummyPg(),
        branch_report=VolumeBranchReport(),
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


def _list_tools(client: TestClient) -> list[dict]:
    response = client.post(
        "/mcp",
        headers={
            "x-api-key": "top-secret",
            "accept": "application/json",
            "mcp-protocol-version": "2025-06-18",
            "host": "mcp.example.test",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    return response.json()["result"]["tools"]


def test_controlled_list_envelope_truncates_large_dataset():
    rows = [{"id": index, "name": "X" * 400, "description": "Y" * 600} for index in range(1, 40)]
    payload = build_controlled_list_envelope(
        source="odoo",
        rows=rows,
        total_count=39,
        offset=0,
        limit=50,
        detail_level="summary",
        summary_fields=["id", "name", "description"],
        standard_fields=["id", "name", "description"],
    )

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["truncated"] is True
    assert len(payload["items"]) <= 8
    assert len(payload["items"][0]["name"]) < 120
    assert payload["next_cursor"] is not None


def test_search_tasks_schema_exposes_project_and_assignee_filters():
    with build_volume_test_client() as client:
        tools = _list_tools(client)

    search_tasks_tool = next(tool for tool in tools if tool["name"] == "search_tasks")
    get_task_tool = next(tool for tool in tools if tool["name"] == "get_task_by_id")
    properties = search_tasks_tool["inputSchema"]["properties"]
    assert "project_ids" in properties
    assert "assignee_ids" in properties
    assert "stage_ids" in properties
    assert "detail_level" in properties
    assert "assignees" in search_tasks_tool["description"]
    assert get_task_tool["name"] == "get_task_by_id"


def test_search_projects_is_accent_tolerant():
    with build_volume_test_client() as client:
        accented = _call_tool(client, "search_projects", {"query": "Biométricos"})
        plain = _call_tool(client, "search_projects", {"query": "biometricos"})

    assert accented["summary"]["total_count"] == 1
    assert plain["summary"]["total_count"] == 1
    assert accented["items"][0]["id"] == 3
    assert plain["items"][0]["id"] == 3


def test_search_employees_defaults_to_summary_mode_and_small_page():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_employees")

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["truncated"] is True
    assert len(payload["items"]) <= 8
    assert set(payload["items"][0].keys()) <= {"id", "employee_number", "name", "active"}
    assert payload["next_cursor"] is not None


def test_search_employees_full_mode_can_return_extra_fields():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_employees", {"detail_level": "full", "limit": 3})

    assert payload["summary"]["detail_level"] == "full"
    assert len(payload["items"]) == 3
    assert "company_id" in payload["items"][0]
    assert "parent_id" in payload["items"][0]


def test_employee_attendance_summary_default_is_top_n():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "get_employee_attendance_summary")

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["summary"]["ordering"] == "top_worked_hours_desc"
    assert payload["items"][0]["employee_id"] == 20
    assert payload["items"][0]["total_worked_hours"] == 20.0
    assert len(payload["items"]) <= 8
    assert payload["truncated"] is True
    assert payload["next_cursor"] is not None


def test_search_tasks_project_filter_returns_assignees_and_stage_names():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_tasks", {"project_ids": [3]})

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["summary"]["total_count"] == 2
    assert payload["summary"]["pending_count"] == 2
    assert payload["summary"]["aggregation_complete"] is True
    assert payload["summary"]["stage_breakdown"] == [
        {
            "stage_id": 86,
            "stage_name": "Configuración y Pruebas",
            "task_count": 2,
            "pending_count": 2,
            "fold": False,
        }
    ]
    assert payload["summary"]["assignee_breakdown"][0]["task_count"] == 1
    assert len(payload["summary"]["top_pending_tasks"]) == 2
    assert payload["items"][0]["project_name"] == "Biométricos"
    assert payload["items"][0]["stage_name"] == "Configuración y Pruebas"
    assert payload["items"][0]["assignees"][0]["name"] in {"Ivan", "Adriana Mendoza"}


def test_search_tasks_limit_50_handles_malformed_assignee_shape():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_tasks", {"limit": 50})

    assert payload["summary"]["total_count"] == 4
    assert payload["summary"]["pending_count"] == 3
    assert "assignee_shape_recovered" in payload["warnings"]
    assert payload["items"][0]["assignees"]


def test_get_task_by_id_resolves_assignee_names():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "get_task_by_id", {"task_id": 19})

    assert payload["summary"]["found"] is True
    assert payload["items"][0]["project_name"] == "Biométricos"
    assert payload["items"][0]["stage_name"] == "Configuración y Pruebas"
    assert payload["items"][0]["assignees"] == [
        {"id": 16, "name": "Ivan", "login": "ivan@example.test", "active": True}
    ]
