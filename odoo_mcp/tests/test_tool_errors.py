from __future__ import annotations

import json
from dataclasses import dataclass

from starlette.testclient import TestClient

from odoo_mcp.app import create_app
from odoo_mcp.config import Settings
from test_response_volume import build_volume_test_client


class ErrorDummyPg:
    def healthcheck(self) -> dict[str, object]:
        return {"db": "biometric_ingest", "usr": "mcp_readonly", "ok": 1}

    def close(self) -> None:
        return None


class ErrorDummyBranchReport:
    def build_rows(self, **_: object):
        return [], "UTC"


class FailingOdoo:
    def __init__(self, message: str):
        self.message = message

    def healthcheck(self) -> dict[str, object]:
        return {"server_version": "19.0", "authenticated_uid": 999}

    def close(self) -> None:
        return None

    def fields_get(self, _: str) -> dict[str, object]:
        return {
            "id": {"type": "integer"},
            "name": {"type": "char"},
            "display_name": {"type": "char"},
            "active": {"type": "boolean"},
        }

    def existing_fields(self, model: str, candidates: list[str]) -> list[str]:
        known = set(self.fields_get(model))
        return [field for field in candidates if field in known]

    def search_count(self, _: str, __: list[object]) -> int:
        return 0

    def search_read(self, *_: object, **__: object):
        raise RuntimeError(self.message)


@dataclass
class ErrorRuntime:
    settings: Settings
    odoo: FailingOdoo
    biometric_ingest: ErrorDummyPg
    branch_report: ErrorDummyBranchReport

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_error_test_client(message: str) -> TestClient:
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
    runtime = ErrorRuntime(
        settings=settings,
        odoo=FailingOdoo(message),
        biometric_ingest=ErrorDummyPg(),
        branch_report=ErrorDummyBranchReport(),
    )
    return TestClient(create_app(settings=settings, runtime=runtime))


def _call_mcp(client: TestClient, method: str, params: dict | None = None) -> dict:
    response = client.post(
        "/mcp",
        headers={
            "x-api-key": "top-secret",
            "accept": "application/json",
            "mcp-protocol-version": "2025-06-18",
            "host": "mcp.example.test",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )
    assert response.status_code == 200
    return response.json()


def test_invalid_arguments_return_structured_error_payload():
    with build_volume_test_client() as client:
        payload = _call_mcp(client, "tools/call", {"name": "get_task_by_id", "arguments": {"task_id": "oops"}})

    assert payload["result"]["isError"] is True
    error_payload = json.loads(payload["result"]["content"][0]["text"])
    assert error_payload["error_code"] == "invalid_arguments"
    assert error_payload["retryable"] is False
    assert payload["result"]["structuredContent"] == error_payload


def test_unknown_tool_returns_structured_error_payload():
    with build_volume_test_client() as client:
        payload = _call_mcp(client, "tools/call", {"name": "does_not_exist", "arguments": {}})

    assert payload["result"]["isError"] is True
    error_payload = json.loads(payload["result"]["content"][0]["text"])
    assert error_payload["error_code"] == "unknown_tool"
    assert error_payload["retryable"] is False
    assert payload["result"]["structuredContent"] == error_payload


def test_backend_request_errors_are_retryable_and_structured():
    with build_error_test_client("Request-sent") as client:
        payload = _call_mcp(client, "tools/call", {"name": "search_projects", "arguments": {"query": "bio"}})

    assert payload["result"]["isError"] is True
    error_payload = json.loads(payload["result"]["content"][0]["text"])
    assert error_payload["error_code"] == "backend_request_error"
    assert error_payload["retryable"] is True
    assert payload["result"]["structuredContent"] == error_payload


def test_internal_execution_errors_are_structured():
    with build_error_test_client("invalid literal for int() with base 10: 'id'") as client:
        payload = _call_mcp(client, "tools/call", {"name": "search_projects", "arguments": {"query": "bio"}})

    assert payload["result"]["isError"] is True
    error_payload = json.loads(payload["result"]["content"][0]["text"])
    assert error_payload["error_code"] == "internal_execution_error"
    assert error_payload["retryable"] is False
