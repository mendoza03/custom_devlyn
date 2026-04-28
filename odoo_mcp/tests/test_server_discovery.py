from __future__ import annotations

import json

from test_app_auth import build_test_client


def _mcp_call(method: str, params: dict | None = None) -> dict:
    headers = {
        "x-api-key": "top-secret",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2025-06-18",
        "host": "mcp.example.test",
    }
    with build_test_client() as client:
        response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    assert response.status_code == 200
    payload = response.json()
    assert "result" in payload
    return payload["result"]


def test_resources_list_exposes_llm_guides():
    result = _mcp_call("resources/list")
    resources = {item["uri"] for item in result["resources"]}

    assert "odoo-mcp://server/overview" in resources
    assert "odoo-mcp://server/tool-catalog" in resources
    assert "odoo-mcp://server/usage-guide" in resources
    assert "odoo-mcp://server/response-envelope" in resources
    assert "odoo-mcp://server/filter-reference" in resources

    templates = _mcp_call("resources/templates/list")
    uris = {item["uriTemplate"] for item in templates["resourceTemplates"]}
    assert "odoo-mcp://schemas/{domain_name}" in uris


def test_tools_list_exposes_v2_ergonomics():
    result = _mcp_call("tools/list")
    tools = {item["name"]: item for item in result["tools"]}

    for tool_name in {
        "count_employees",
        "get_employee_by_id",
        "count_attendance_records",
        "get_attendance_record_by_id",
        "count_hr_biometric_events",
        "get_hr_biometric_event_by_id",
        "count_dahua_normalized_events",
        "get_dahua_normalized_event_by_id",
        "count_helpdesk_tickets",
        "get_helpdesk_catalogs",
        "describe_helpdesk_ticket_schema",
        "get_helpdesk_ticket_by_id",
    }:
        assert tool_name in tools

    assert "summary.total_count" in tools["search_employees"]["description"]
    assert "summary.matched_count" in tools["count_employees"]["description"]
    assert "warnings=['not_found']" in tools["get_employee_by_id"]["description"]

    biometric_schema = json.dumps(tools["search_hr_biometric_events"]["inputSchema"])
    assert "check_out_written" in biometric_schema
    assert "employee_not_found" in biometric_schema

    branch_schema = json.dumps(tools["get_branch_attendance_report"]["inputSchema"])
    assert "mapped_only" in branch_schema
    assert "sin_sucursal_only" in branch_schema

    normalized_schema = json.dumps(tools["search_dahua_normalized_events"]["inputSchema"])
    assert "entry" in normalized_schema
    assert "exit" in normalized_schema
    assert "unknown" in normalized_schema

    device_schema = json.dumps(tools["get_dahua_device_status"]["inputSchema"])
    assert "online" in device_schema
    assert "stale" in device_schema
    assert "offline" in device_schema

    attendance_description = tools["search_attendance_records"]["description"]
    assert "get_branch_attendance_report" in attendance_description
    assert "get_devlyn_catalogs" in attendance_description
