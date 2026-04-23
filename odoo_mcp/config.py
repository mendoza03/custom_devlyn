from __future__ import annotations

import os
from dataclasses import dataclass

from odoo_mcp import __version__


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    public_base_url: str
    mcp_mount_path: str
    host: str
    port: int
    mcp_api_key: str
    odoo_url: str
    odoo_db: str
    odoo_login: str
    odoo_api_key: str
    odoo_locale: str
    odoo_timeout_seconds: int
    biometric_pg_dsn: str
    biometric_pg_connect_timeout_seconds: int
    biometric_pg_statement_timeout_ms: int
    default_limit: int
    max_limit: int
    default_window_days: int
    cache_ttl_seconds: int
    default_timezone: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        mount_path = os.getenv("ODOO_MCP_MOUNT_PATH", "/mcp").strip() or "/mcp"
        if not mount_path.startswith("/"):
            mount_path = f"/{mount_path}"

        return cls(
            app_name=os.getenv("ODOO_MCP_APP_NAME", "Devlyn Odoo Attendance MCP").strip()
            or "Devlyn Odoo Attendance MCP",
            app_version=os.getenv("ODOO_MCP_APP_VERSION", __version__).strip() or __version__,
            public_base_url=_require("ODOO_MCP_PUBLIC_BASE_URL").rstrip("/"),
            mcp_mount_path=mount_path,
            host=os.getenv("ODOO_MCP_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=_int("ODOO_MCP_PORT", 8071),
            mcp_api_key=_require("ODOO_MCP_API_KEY"),
            odoo_url=_require("ODOO_MCP_ODOO_URL").rstrip("/"),
            odoo_db=_require("ODOO_MCP_ODOO_DB"),
            odoo_login=_require("ODOO_MCP_ODOO_LOGIN"),
            odoo_api_key=_require("ODOO_MCP_ODOO_API_KEY"),
            odoo_locale=os.getenv("ODOO_MCP_ODOO_LOCALE", "es_MX").strip() or "es_MX",
            odoo_timeout_seconds=_int("ODOO_MCP_ODOO_TIMEOUT_SECONDS", 15),
            biometric_pg_dsn=_require("ODOO_MCP_BIOMETRIC_PG_DSN"),
            biometric_pg_connect_timeout_seconds=_int("ODOO_MCP_BIOMETRIC_PG_CONNECT_TIMEOUT_SECONDS", 5),
            biometric_pg_statement_timeout_ms=_int("ODOO_MCP_BIOMETRIC_PG_STATEMENT_TIMEOUT_MS", 5000),
            default_limit=_int("ODOO_MCP_DEFAULT_LIMIT", 50),
            max_limit=_int("ODOO_MCP_MAX_LIMIT", 200),
            default_window_days=_int("ODOO_MCP_DEFAULT_WINDOW_DAYS", 7),
            cache_ttl_seconds=_int("ODOO_MCP_CACHE_TTL_SECONDS", 300),
            default_timezone=os.getenv("ODOO_MCP_DEFAULT_TIMEZONE", "America/Mexico_City").strip()
            or "America/Mexico_City",
            log_level=os.getenv("ODOO_MCP_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        )
