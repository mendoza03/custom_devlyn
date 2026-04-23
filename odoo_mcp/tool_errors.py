from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from odoo_mcp.json_utils import dumps_text, loads


TOOL_PREFIX_PATTERN = re.compile(r"^Error executing tool (?P<tool_name>[\w\-]+): (?P<message>.+)$", re.DOTALL)
BACKEND_REQUEST_TERMS = (
    "idle",
    "request-sent",
    "timeout",
    "timed out",
    "connection refused",
    "connection reset",
    "connection aborted",
    "connecttimeout",
    "readtimeout",
    "remote disconnected",
    "temporarily unavailable",
)


@dataclass(frozen=True)
class ToolErrorPayload:
    error_code: str
    message: str
    retryable: bool
    suggested_arguments: dict[str, Any]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
            "suggested_arguments": self.suggested_arguments,
            "details": self.details,
        }


def _extract_tool_error_text(payload: dict[str, Any]) -> str | None:
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("isError") is not True:
        return None
    content = result.get("content")
    if not isinstance(content, list) or not content:
        return None
    first_item = content[0]
    if not isinstance(first_item, dict):
        return None
    text = first_item.get("text")
    return text if isinstance(text, str) else None


def _normalize_error_payload(raw_message: str) -> dict[str, Any]:
    message = raw_message.strip()
    details: dict[str, Any] = {"raw_message": message}
    match = TOOL_PREFIX_PATTERN.match(message)
    if match:
        details["tool_name"] = match.group("tool_name")
        message = match.group("message").strip()

    existing_payload: dict[str, Any] | None = None
    try:
        candidate = loads(message)
        if isinstance(candidate, dict):
            existing_payload = candidate
    except Exception:
        existing_payload = None

    if existing_payload and {"error_code", "message", "retryable", "suggested_arguments", "details"} <= set(existing_payload):
        return existing_payload

    lowered = message.casefold()
    if message.startswith("Input validation error:") or (
        "validation error" in lowered and ("input should be" in lowered or "type=" in lowered)
    ):
        payload = ToolErrorPayload(
            error_code="invalid_arguments",
            message=message,
            retryable=False,
            suggested_arguments={},
            details=details,
        )
    elif message.startswith("Unknown tool:"):
        payload = ToolErrorPayload(
            error_code="unknown_tool",
            message=message,
            retryable=False,
            suggested_arguments={},
            details=details,
        )
    elif any(term in lowered for term in BACKEND_REQUEST_TERMS):
        payload = ToolErrorPayload(
            error_code="backend_request_error",
            message=message,
            retryable=True,
            suggested_arguments={},
            details=details,
        )
    else:
        payload = ToolErrorPayload(
            error_code="internal_execution_error",
            message=message,
            retryable=False,
            suggested_arguments={},
            details=details,
        )
    return payload.to_dict()


def rewrite_tool_error_response(payload: dict[str, Any]) -> dict[str, Any] | None:
    message = _extract_tool_error_text(payload)
    if message is None:
        return None

    error_payload = _normalize_error_payload(message)
    result = dict(payload["result"])
    result["content"] = [{"type": "text", "text": dumps_text(error_payload)}]
    result["structuredContent"] = error_payload
    result["isError"] = True
    return {**payload, "result": result}


class McpStructuredToolErrorMiddleware:
    def __init__(self, app: ASGIApp, *, mcp_path: str):
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") != self.mcp_path:
            await self.app(scope, receive, send)
            return

        start_message: Message | None = None
        body_chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start_message, body_chunks
            if message["type"] == "http.response.start":
                start_message = message
                return

            if message["type"] != "http.response.body" or start_message is None:
                await send(message)
                return

            body_chunks.append(message.get("body", b""))
            if message.get("more_body", False):
                return

            body = b"".join(body_chunks)
            rewritten_body = body
            raw_headers = list(start_message["headers"])
            headers = MutableHeaders(raw=raw_headers)
            if headers.get("content-type", "").startswith("application/json") and body:
                try:
                    payload = loads(body)
                    rewritten = rewrite_tool_error_response(payload) if isinstance(payload, dict) else None
                    if rewritten is not None:
                        rewritten_body = dumps_text(rewritten).encode("utf-8")
                except Exception:
                    rewritten_body = body

            headers["content-length"] = str(len(rewritten_body))
            start_message["headers"] = raw_headers
            await send(start_message)
            await send({"type": "http.response.body", "body": rewritten_body, "more_body": False})

        await self.app(scope, receive, send_wrapper)
