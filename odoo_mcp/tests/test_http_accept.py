from __future__ import annotations

import json

import pytest

from odoo_mcp.http_accept import accepts_media_type, normalized_post_accept_header
from test_app_auth import build_test_client


INITIALIZE_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "0.1.0"},
    },
}


def _mcp_headers(accept: str | None) -> dict[str, str]:
    headers = {
        "x-api-key": "top-secret",
        "mcp-protocol-version": "2025-06-18",
        "host": "mcp.example.test",
    }
    if accept is not None:
        headers["accept"] = accept
    return headers


@pytest.mark.parametrize(
    ("accept_header", "expected"),
    [
        ("application/json", True),
        ("application/json; charset=utf-8", True),
        ("application/json;q=0.9, text/event-stream", True),
        ("*/*", True),
        ("application/*", True),
        ("application/json;q=0, */*;q=0.8", False),
        ("application/json;q=0", False),
        ("text/plain", False),
        (None, True),
    ],
)
def test_accepts_media_type_matches_rfcish_expectations(accept_header: str | None, expected: bool):
    assert accepts_media_type(accept_header, "application/json") is expected


def test_normalized_post_accept_header_handles_missing_and_wildcards():
    assert normalized_post_accept_header(None) == "application/json"
    assert normalized_post_accept_header("") == "application/json"
    assert normalized_post_accept_header("*/*") == "application/json, */*"
    assert normalized_post_accept_header("application/*") == "application/json, application/*"
    assert normalized_post_accept_header("application/json, text/event-stream") is None
    assert normalized_post_accept_header("text/plain") is None


@pytest.mark.parametrize(
    "accept_header",
    [
        "application/json",
        "application/json, text/event-stream",
        "text/event-stream, application/json;q=0.9",
        "*/*",
        "",
    ],
)
def test_post_initialize_accept_variants_return_json_success(accept_header: str):
    with build_test_client() as client:
        response = client.post("/mcp", headers=_mcp_headers(accept_header), json=INITIALIZE_BODY)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["result"]["protocolVersion"] == "2025-06-18"


def test_post_requests_keep_expected_status_codes_with_wildcard_accept():
    headers = _mcp_headers("*/*")
    with build_test_client() as client:
        initialize = client.post("/mcp", headers=headers, json=INITIALIZE_BODY)
        initialized = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools_list = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_call = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "describe_server_capabilities", "arguments": {}}},
        )

    assert initialize.status_code == 200
    assert initialize.headers["content-type"].startswith("application/json")
    assert initialized.status_code == 202
    assert initialized.text == ""
    assert tools_list.status_code == 200
    assert tools_list.headers["content-type"].startswith("application/json")
    assert tools_call.status_code == 200
    assert tools_call.headers["content-type"].startswith("application/json")


def test_incompatible_accept_still_returns_406():
    with build_test_client() as client:
        response = client.post("/mcp", headers=_mcp_headers("text/plain"), json=INITIALIZE_BODY)

    assert response.status_code == 406
    payload = response.json()
    assert payload["error"]["message"] == "Not Acceptable: Client must accept application/json"


def test_accept_absent_normalizer_semantics_are_explicit():
    assert normalized_post_accept_header(None) == "application/json"
