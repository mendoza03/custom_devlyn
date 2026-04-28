from __future__ import annotations

import threading
import xmlrpc.client
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from odoo_mcp.cache import TTLCache


def _normalize_relation_value(item: Any, field_info: dict[str, Any] | None) -> Any:
    field_type = str((field_info or {}).get("type") or "").strip()
    if field_type == "many2one":
        if isinstance(item, (list, tuple)):
            if len(item) >= 2:
                return {"id": item[0], "display_name": item[1]}
            if len(item) == 1:
                return {"id": item[0], "display_name": None}
        return item

    if field_type in {"many2many", "one2many"}:
        if isinstance(item, (list, tuple)):
            normalized: list[int] = []
            for candidate in item:
                try:
                    normalized.append(int(candidate))
                except (TypeError, ValueError):
                    return list(item)
            return normalized
        return item

    return item


def _normalize_record(value: dict[str, Any], field_map: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized[key] = _normalize_relation_value(item, field_map.get(key))
    return normalized


class TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, timeout: int):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host: str):
        connection = super().make_connection(host)
        connection.timeout = self._timeout
        return connection


class TimeoutHttpTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: int):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host: str):
        connection = super().make_connection(host)
        connection.timeout = self._timeout
        return connection


class TimeoutServerProxy(xmlrpc.client.ServerProxy):
    def __init__(self, uri: str, timeout: int):
        parsed = urlparse(uri)
        transport: xmlrpc.client.Transport
        if parsed.scheme == "https":
            transport = TimeoutSafeTransport(timeout)
        else:
            transport = TimeoutHttpTransport(timeout)
        super().__init__(uri, transport=transport, allow_none=True)


class OdooBackend:
    def __init__(
        self,
        *,
        url: str,
        db: str,
        login: str,
        api_key: str,
        locale: str,
        timeout_seconds: int,
        cache_ttl_seconds: int,
    ):
        self.url = url.rstrip("/")
        self.db = db
        self.login = login
        self.api_key = api_key
        self.locale = locale
        self.timeout_seconds = timeout_seconds
        self._common = TimeoutServerProxy(f"{self.url}/xmlrpc/2/common", timeout_seconds)
        self._object = TimeoutServerProxy(f"{self.url}/xmlrpc/2/object", timeout_seconds)
        self._uid: int | None = None
        self._uid_lock = threading.Lock()
        self._common_lock = threading.Lock()
        self._object_lock = threading.Lock()
        self._fields_cache: TTLCache[dict[str, Any]] = TTLCache(cache_ttl_seconds)
        self._catalog_cache: TTLCache[dict[str, list[dict[str, Any]]]] = TTLCache(cache_ttl_seconds)

    def _context(self) -> dict[str, Any]:
        return {"lang": self.locale}

    def authenticate(self) -> int:
        with self._uid_lock:
            if self._uid is not None:
                return self._uid
            with self._common_lock:
                uid = self._common.authenticate(self.db, self.login, self.api_key, {})
            if not uid:
                raise RuntimeError("Odoo XML-RPC authentication failed for MCP backend")
            self._uid = int(uid)
            return self._uid

    def call(self, model: str, method: str, args: Iterable[Any] | None = None, kwargs: dict[str, Any] | None = None):
        uid = self.authenticate()
        args = list(args or [])
        payload = dict(kwargs or {})
        payload.setdefault("context", self._context())
        with self._object_lock:
            return self._object.execute_kw(self.db, uid, self.api_key, model, method, args, payload)

    def search_count(self, model: str, domain: list[Any]) -> int:
        return int(self.call(model, "search_count", [domain]))

    def search(self, model: str, domain: list[Any], *, limit: int, offset: int = 0, order: str | None = None) -> list[int]:
        kwargs: dict[str, Any] = {"offset": offset, "limit": limit}
        if order:
            kwargs["order"] = order
        ids = self.call(model, "search", [domain], kwargs)
        return [int(item) for item in ids]

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        field_map = self.fields_get(model)
        rows = self.call(model, "read", [ids], {"fields": fields})
        return [_normalize_record(dict(row), field_map) for row in rows]

    def search_read(
        self,
        model: str,
        domain: list[Any],
        *,
        fields: list[str],
        limit: int,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"fields": fields, "limit": limit, "offset": offset}
        if order:
            kwargs["order"] = order
        field_map = self.fields_get(model)
        rows = self.call(model, "search_read", [domain], kwargs)
        return [_normalize_record(dict(row), field_map) for row in rows]

    def fields_get(self, model: str) -> dict[str, Any]:
        cached = self._fields_cache.get(model)
        if cached is not None:
            return cached
        fields = self.call(
            model,
            "fields_get",
            [],
            {"attributes": ["type", "string", "relation", "selection", "store", "readonly", "required"]},
        )
        return self._fields_cache.set(model, dict(fields))

    def existing_fields(self, model: str, candidates: list[str]) -> list[str]:
        fields = self.fields_get(model)
        return [field for field in candidates if field in fields]

    def healthcheck(self) -> dict[str, Any]:
        with self._common_lock:
            version = self._common.version()
        return {
            "server_version": version.get("server_version"),
            "server_serie": version.get("server_serie"),
            "authenticated_uid": self.authenticate(),
        }

    def get_timezone_name(self, fallback_timezone: str) -> str:
        fields = self.existing_fields("hr.biometric.sync.config", ["timezone_name"])
        if not fields:
            return fallback_timezone
        rows = self.search_read("hr.biometric.sync.config", [], fields=fields, limit=1)
        if not rows:
            return fallback_timezone
        timezone_name = str(rows[0].get("timezone_name") or "").strip()
        return timezone_name or fallback_timezone

    def get_devlyn_catalogs(self) -> dict[str, list[dict[str, Any]]]:
        cached = self._catalog_cache.get("devlyn_catalogs")
        if cached is not None:
            return cached

        catalogs = {
            "regions": self.search_read(
                "devlyn.catalog.region",
                [("active", "=", True)],
                fields=self.existing_fields("devlyn.catalog.region", ["id", "name", "legacy_region_id", "active"]),
                limit=5000,
                order="name asc",
            ),
            "zones": self.search_read(
                "devlyn.catalog.zone",
                [("active", "=", True)],
                fields=self.existing_fields(
                    "devlyn.catalog.zone", ["id", "name", "legacy_zone_id", "region_id", "active"]
                ),
                limit=5000,
                order="name asc",
            ),
            "districts": self.search_read(
                "devlyn.catalog.district",
                [("active", "=", True)],
                fields=self.existing_fields(
                    "devlyn.catalog.district",
                    ["id", "name", "legacy_district_id", "region_id", "zone_id", "active"],
                ),
                limit=5000,
                order="name asc",
            ),
            "formats": self.search_read(
                "devlyn.catalog.format",
                [("active", "=", True)],
                fields=self.existing_fields("devlyn.catalog.format", ["id", "name", "active"]),
                limit=5000,
                order="name asc",
            ),
            "statuses": self.search_read(
                "devlyn.catalog.status",
                [("active", "=", True)],
                fields=self.existing_fields("devlyn.catalog.status", ["id", "name", "active"]),
                limit=5000,
                order="name asc",
            ),
            "optical_levels": self.search_read(
                "devlyn.catalog.optical.level",
                [("active", "=", True)],
                fields=self.existing_fields("devlyn.catalog.optical.level", ["id", "code", "name", "active"]),
                limit=5000,
                order="code asc",
            ),
            "branches": self.search_read(
                "devlyn.catalog.branch",
                [("active", "=", True)],
                fields=self.existing_fields(
                    "devlyn.catalog.branch",
                    [
                        "id",
                        "name",
                        "center_code",
                        "branch_code",
                        "branch_name",
                        "optical_level_id",
                        "format_id",
                        "status_id",
                        "region_id",
                        "zone_id",
                        "district_id",
                        "active",
                    ],
                ),
                limit=5000,
                order="center_code asc",
            ),
        }
        return self._catalog_cache.set("devlyn_catalogs", catalogs)

    def close(self) -> None:
        return None
