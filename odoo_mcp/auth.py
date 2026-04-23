from __future__ import annotations

import hmac
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from odoo_mcp.json_utils import json_response_payload


def _extract_presented_key(request: Request) -> str | None:
    header_key = request.headers.get("x-api-key", "").strip()
    if header_key:
        return header_key

    auth = request.headers.get("authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


@dataclass(frozen=True)
class AuthCheckResult:
    ok: bool
    status_code: int
    reason: str


class ApiKeyAuthorizer:
    def __init__(self, expected_key: str):
        self._expected_key = expected_key

    def check(self, request: Request) -> AuthCheckResult:
        presented = _extract_presented_key(request)
        if not presented:
            return AuthCheckResult(ok=False, status_code=HTTP_401_UNAUTHORIZED, reason="missing_api_key")
        if not hmac.compare_digest(presented, self._expected_key):
            return AuthCheckResult(ok=False, status_code=HTTP_403_FORBIDDEN, reason="invalid_api_key")
        return AuthCheckResult(ok=True, status_code=HTTP_200_OK, reason="ok")


class ApiKeyMiddleware:
    def __init__(self, app: ASGIApp, authorizer: ApiKeyAuthorizer):
        self.app = app
        self.authorizer = authorizer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/healthz":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        result = self.authorizer.check(request)
        if result.ok:
            async def receive_again() -> Message:
                return await request.receive()

            await self.app(scope, receive_again, send)
            return

        body = json_response_payload({"ok": False, "error": result.reason})
        response = Response(body, status_code=result.status_code, media_type="application/json")
        await response(scope, receive, send)
