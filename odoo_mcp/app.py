from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

from odoo_mcp.auth import ApiKeyAuthorizer, ApiKeyMiddleware
from odoo_mcp.config import Settings
from odoo_mcp.http_accept import McpPostAcceptCompatibilityMiddleware
from odoo_mcp.json_utils import json_response_payload
from odoo_mcp.server import Runtime, build_mcp_server, build_runtime
from odoo_mcp.tool_errors import McpStructuredToolErrorMiddleware


def _json_response(payload: dict, status_code: int = 200) -> Response:
    return Response(json_response_payload(payload), status_code=status_code, media_type="application/json")


def create_app(settings: Settings | None = None, runtime: Runtime | None = None) -> Starlette:
    settings = settings or Settings.from_env()
    runtime = runtime or build_runtime(settings)
    mcp_server = build_mcp_server(runtime)
    app = mcp_server.streamable_http_app()
    inner_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(inner_app: Starlette):
        async with inner_lifespan(inner_app):
            try:
                yield
            finally:
                await asyncio.to_thread(runtime.close)

    async def healthz(_: Request) -> Response:
        return _json_response({"ok": True, "name": settings.app_name, "version": settings.app_version})

    async def readyz(_: Request) -> Response:
        odoo = await asyncio.to_thread(runtime.odoo.healthcheck)
        pg = await asyncio.to_thread(runtime.biometric_ingest.healthcheck)
        return _json_response({"ok": True, "odoo": odoo, "biometric_ingest": pg})

    async def version(_: Request) -> Response:
        payload = {
            "ok": True,
            "name": settings.app_name,
            "version": settings.app_version,
            "public_url": f"{settings.public_base_url}{settings.mcp_mount_path}",
            "transport": "streamable-http",
        }
        return _json_response(payload)

    app.add_route("/healthz", healthz, methods=["GET"])
    app.add_route("/readyz", readyz, methods=["GET"])
    app.add_route("/version", version, methods=["GET"])
    app.router.lifespan_context = lifespan
    app.add_middleware(McpStructuredToolErrorMiddleware, mcp_path=settings.mcp_mount_path)
    app.add_middleware(McpPostAcceptCompatibilityMiddleware, mcp_path=settings.mcp_mount_path)
    app.add_middleware(ApiKeyMiddleware, authorizer=ApiKeyAuthorizer(settings.mcp_api_key))
    app.state.settings = settings
    app.state.runtime = runtime
    app.state.mcp_server = mcp_server
    return app
