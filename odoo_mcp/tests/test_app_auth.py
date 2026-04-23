from __future__ import annotations

from dataclasses import dataclass

from starlette.testclient import TestClient

from odoo_mcp.app import create_app
from odoo_mcp.config import Settings


class DummyOdoo:
    def healthcheck(self) -> dict[str, object]:
        return {"server_version": "19.0", "authenticated_uid": 999}

    def close(self) -> None:
        return None


class DummyPg:
    def healthcheck(self) -> dict[str, object]:
        return {"db": "biometric_ingest", "usr": "mcp_readonly", "ok": 1}

    def close(self) -> None:
        return None


class DummyBranchReport:
    def build_rows(self, **_: object):
        return [], "UTC"


@dataclass
class DummyRuntime:
    settings: Settings
    odoo: DummyOdoo
    biometric_ingest: DummyPg
    branch_report: DummyBranchReport

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_test_client() -> TestClient:
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
    runtime = DummyRuntime(settings=settings, odoo=DummyOdoo(), biometric_ingest=DummyPg(), branch_report=DummyBranchReport())
    return TestClient(create_app(settings=settings, runtime=runtime))


def test_healthz_bypasses_authentication():
    with build_test_client() as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_version_requires_valid_api_key():
    with build_test_client() as client:
        missing = client.get("/version")
        invalid = client.get("/version", headers={"x-api-key": "wrong"})
        valid = client.get("/version", headers={"x-api-key": "top-secret"})
        bearer = client.get("/version", headers={"authorization": "Bearer top-secret"})

    assert missing.status_code == 401
    assert invalid.status_code == 403
    assert valid.status_code == 200
    assert bearer.status_code == 200
    assert valid.json()["public_url"] == "https://mcp.example.test/mcp"


def test_readyz_and_mcp_route_are_protected():
    with build_test_client() as client:
        ready = client.get("/readyz", headers={"x-api-key": "top-secret"})
        blocked = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert ready.status_code == 200
    assert ready.json()["odoo"]["authenticated_uid"] == 999
    assert blocked.status_code == 401
