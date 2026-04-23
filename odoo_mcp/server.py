from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
import unicodedata
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from odoo_mcp import __version__
from odoo_mcp.backends import BiometricIngestBackend, OdooBackend
from odoo_mcp.branch_report import BranchAttendanceReportService, to_local_datetime, utc_bounds_for_local_dates
from odoo_mcp.config import Settings
from odoo_mcp.cursor import decode_offset_cursor, encode_offset_cursor
from odoo_mcp.json_utils import dumps_text


ResolutionScope = Literal["all", "mapped_only", "sin_sucursal_only"]
SyncStatus = Literal[
    "pending",
    "check_in_created",
    "check_out_written",
    "duplicate_ignored",
    "employee_not_found",
    "denied_ignored",
    "after_close_review",
    "error",
]
DirectionFilter = Literal["entry", "exit", "unknown"]
DeviceOperationalStatus = Literal["online", "stale", "offline"]
DetailLevel = Literal["summary", "standard", "full"]

STANDARD_ENVELOPE_FIELDS = ["source", "summary", "items", "next_cursor", "applied_defaults", "warnings", "truncated"]
STANDARD_ENVELOPE_DESCRIPTION = (
    "All search tools return the standard envelope with `source`, `summary`, `items`, `next_cursor`, "
    "`applied_defaults`, `warnings`, and `truncated`. Read `summary.total_count` before paging further."
)
PAGINATION_DESCRIPTION = "Use `limit` plus `cursor` for incremental exploration instead of requesting full datasets."
COUNT_DESCRIPTION = "Count tools return no rows in `items`; read `summary.matched_count`."
DETAIL_DESCRIPTION = (
    "Detail tools return a single item when found, or an empty `items` list with `warnings=['not_found']`."
)
DETAIL_LEVEL_DESCRIPTION = (
    "List-like tools accept `detail_level=summary|standard|full`. The default is `summary` to minimize response size."
)
DEFAULT_LIMIT_BY_LEVEL: dict[DetailLevel, int] = {"summary": 10, "standard": 25, "full": 50}
MAX_ITEMS_BY_LEVEL: dict[DetailLevel, int] = {"summary": 8, "standard": 20, "full": 50}
TEXT_LIMIT_BY_LEVEL: dict[DetailLevel, int] = {"summary": 96, "standard": 180, "full": 480}
CHAR_BUDGET_BY_LEVEL: dict[DetailLevel, int] = {"summary": 2800, "standard": 6500, "full": 14000}
TASK_SUMMARY_SAMPLE_LIMIT = 1000
TOP_PENDING_TASK_LIMIT = 5


def clamp_limit(limit: int | None, *, default: int, max_limit: int) -> int:
    value = default if limit in (None, 0) else int(limit)
    return max(1, min(value, max_limit))


def default_date_range(window_days: int) -> tuple[date, date]:
    end = datetime.now(tz=UTC).date()
    start = end - timedelta(days=window_days - 1)
    return start, end


def parse_date_or_none(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def build_envelope(
    *,
    source: str,
    items: list[dict[str, Any]],
    total_count: int,
    limit: int,
    offset: int,
    applied_defaults: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    returned_count = len(items)
    next_cursor = encode_offset_cursor(offset + returned_count) if offset + returned_count < total_count else None
    merged_summary = {"total_count": total_count, "returned_count": returned_count, "limit": limit, "offset": offset}
    if summary:
        merged_summary.update(summary)
    return {
        "source": source,
        "summary": merged_summary,
        "items": items,
        "next_cursor": next_cursor,
        "applied_defaults": applied_defaults or {},
        "warnings": warnings or [],
        "truncated": truncated,
    }


def build_count_result(
    *,
    source: str,
    matched_count: int,
    applied_defaults: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_summary = {"matched_count": matched_count}
    if summary:
        merged_summary.update(summary)
    return {
        "source": source,
        "summary": merged_summary,
        "items": [],
        "next_cursor": None,
        "applied_defaults": applied_defaults or {},
        "warnings": warnings or [],
        "truncated": False,
    }


def build_single_record_result(
    *,
    source: str,
    item: dict[str, Any] | None,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged_summary = {"found": item is not None}
    if summary:
        merged_summary.update(summary)
    return build_envelope(
        source=source,
        items=[item] if item is not None else [],
        total_count=1 if item is not None else 0,
        limit=1,
        offset=0,
        warnings=warnings,
        summary=merged_summary,
    )


def _coerce_relation_ids(values: list[int] | None) -> list[int]:
    return [int(item) for item in (values or [])]


def _merge_requested_fields(base_fields: list[str], include_fields: list[str] | None) -> list[str]:
    ordered = list(base_fields)
    for field in include_fields or []:
        field_name = str(field).strip()
        if field_name and field_name not in ordered:
            ordered.append(field_name)
    return ordered


def _field_set_for_level(
    *,
    detail_level: DetailLevel,
    summary_fields: list[str],
    standard_fields: list[str],
    full_fields: list[str] | None = None,
    include_fields: list[str] | None = None,
) -> list[str]:
    if detail_level == "summary":
        base_fields = summary_fields
    elif detail_level == "standard":
        base_fields = standard_fields
    else:
        base_fields = full_fields or standard_fields
    return _merge_requested_fields(base_fields, include_fields)


def _resolve_text_limit(detail_level: DetailLevel, truncate_text: int | None) -> int | None:
    if truncate_text is None:
        return TEXT_LIMIT_BY_LEVEL[detail_level]
    if int(truncate_text) <= 0:
        return None
    return int(truncate_text)


def _truncate_string(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    if max_chars <= 16:
        return value[:max_chars]
    hidden = len(value) - (max_chars - 12)
    return f"{value[: max_chars - 12]}...(+{hidden})"


def _truncate_nested_value(value: Any, text_limit: int | None) -> Any:
    if text_limit is None:
        return value
    if isinstance(value, str):
        return _truncate_string(value, text_limit)
    if isinstance(value, dict):
        return {key: _truncate_nested_value(item, text_limit) for key, item in value.items()}
    if isinstance(value, list):
        return [_truncate_nested_value(item, text_limit) for item in value]
    return value


def _project_item(item: dict[str, Any], fields: list[str], text_limit: int | None) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for field in fields:
        if field in item:
            projected[field] = _truncate_nested_value(item[field], text_limit)
    return projected


def _format_timestamp_value(value: Any, *, timezone_name: str, fallback_timezone: str) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    localized = to_local_datetime(value, timezone_name, fallback_timezone)
    return localized.isoformat() if localized else value


def _format_timestamp_fields(
    rows: list[dict[str, Any]],
    *,
    field_names: list[str],
    timezone_name: str,
    fallback_timezone: str,
) -> list[dict[str, Any]]:
    if not rows or not field_names:
        return rows

    formatted_rows: list[dict[str, Any]] = []
    for row in rows:
        formatted_row = dict(row)
        for field_name in field_names:
            if field_name in formatted_row:
                formatted_row[field_name] = _format_timestamp_value(
                    formatted_row[field_name],
                    timezone_name=timezone_name,
                    fallback_timezone=fallback_timezone,
                )
        formatted_rows.append(formatted_row)
    return formatted_rows


def _fold_search_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character)).casefold()


def _relation_display_name(value: Any) -> str | None:
    if isinstance(value, dict):
        display_name = str(value.get("display_name") or "").strip()
        return display_name or None
    return None


def _resolve_user_briefs(odoo: OdooBackend, user_ids: list[int]) -> dict[int, dict[str, Any]]:
    unique_ids = sorted({int(user_id) for user_id in user_ids})
    if not unique_ids:
        return {}
    fields = odoo.existing_fields("res.users", ["id", "name", "login", "active"])
    rows = odoo.read("res.users", unique_ids, fields)
    user_map: dict[int, dict[str, Any]] = {}
    for row in rows:
        user_id = row.get("id")
        if not user_id:
            continue
        user_map[int(user_id)] = {
            "id": int(user_id),
            "name": row.get("name"),
            "login": row.get("login"),
            "active": row.get("active"),
        }
    return user_map


def _coerce_task_user_ids(value: Any) -> tuple[list[int], bool]:
    if value in (None, False):
        return [], False

    recovered = False
    if isinstance(value, dict):
        recovered = True
        value = [value.get("id")]
    elif not isinstance(value, (list, tuple, set)):
        recovered = True
        value = [value]

    user_ids: list[int] = []
    for candidate in value:
        raw_value = candidate.get("id") if isinstance(candidate, dict) else candidate
        try:
            user_ids.append(int(raw_value))
        except (TypeError, ValueError):
            recovered = True
    return user_ids, recovered


def _resolve_task_stage_briefs(odoo: OdooBackend, stage_ids: list[int]) -> dict[int, dict[str, Any]]:
    unique_ids = sorted({int(stage_id) for stage_id in stage_ids})
    if not unique_ids:
        return {}
    fields = odoo.existing_fields("project.task.type", ["id", "name", "display_name", "fold", "sequence", "active"])
    rows = odoo.read("project.task.type", unique_ids, fields)
    stage_map: dict[int, dict[str, Any]] = {}
    for row in rows:
        stage_id = row.get("id")
        if not stage_id:
            continue
        stage_map[int(stage_id)] = {
            "id": int(stage_id),
            "name": row.get("name") or row.get("display_name"),
            "display_name": row.get("display_name") or row.get("name"),
            "fold": bool(row.get("fold")),
            "sequence": int(row.get("sequence") or 0),
            "active": row.get("active"),
        }
    return stage_map


def _enrich_task_rows(odoo: OdooBackend, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    task_user_ids: list[int] = []
    task_user_map: list[list[int]] = []
    recovered_user_shape = False
    for row in rows:
        coerced_ids, recovered = _coerce_task_user_ids(row.get("user_ids"))
        task_user_map.append(coerced_ids)
        task_user_ids.extend(coerced_ids)
        recovered_user_shape = recovered_user_shape or recovered
    user_map = _resolve_user_briefs(odoo, task_user_ids)

    enriched_rows: list[dict[str, Any]] = []
    for row, coerced_ids in zip(rows, task_user_map, strict=False):
        task = dict(row)
        task["user_ids"] = coerced_ids
        task["project_name"] = _relation_display_name(task.get("project_id"))
        task["stage_name"] = _relation_display_name(task.get("stage_id"))
        task["assignees"] = [
            user_map.get(int(user_id), {"id": int(user_id), "name": None, "login": None, "active": None})
            for user_id in coerced_ids
        ]
        enriched_rows.append(task)
    warnings = ["assignee_shape_recovered"] if recovered_user_shape else []
    return enriched_rows, warnings


def _build_task_operational_summary(
    odoo: OdooBackend,
    rows: list[dict[str, Any]],
    *,
    aggregation_complete: bool,
    aggregation_sample_size: int,
) -> tuple[dict[str, Any], list[str]]:
    enriched_rows, warnings = _enrich_task_rows(odoo, rows)
    stage_ids = [
        int(stage_id)
        for stage_id in [
            (row.get("stage_id") or {}).get("id")
            for row in enriched_rows
            if isinstance(row.get("stage_id"), dict)
        ]
        if stage_id
    ]
    stage_map = _resolve_task_stage_briefs(odoo, stage_ids)

    pending_count = 0
    stage_buckets: dict[tuple[int | None, str], dict[str, Any]] = {}
    assignee_buckets: dict[tuple[int | None, str], dict[str, Any]] = {}
    pending_rows: list[dict[str, Any]] = []

    for row in enriched_rows:
        stage_ref = row.get("stage_id") if isinstance(row.get("stage_id"), dict) else {}
        stage_id = stage_ref.get("id")
        stage_name = row.get("stage_name") or stage_ref.get("display_name") or "Sin etapa"
        stage_meta = stage_map.get(int(stage_id)) if stage_id else None
        fold = stage_meta["fold"] if stage_meta is not None else None
        sequence = stage_meta["sequence"] if stage_meta is not None else 9999
        is_pending = bool(row.get("active")) and fold is False
        if is_pending:
            pending_count += 1
            pending_rows.append(row)

        stage_key = (int(stage_id) if stage_id else None, stage_name)
        stage_bucket = stage_buckets.setdefault(
            stage_key,
            {
                "stage_id": int(stage_id) if stage_id else None,
                "stage_name": stage_name,
                "task_count": 0,
                "pending_count": 0,
                "fold": fold,
                "sequence": sequence,
            },
        )
        stage_bucket["task_count"] += 1
        if is_pending:
            stage_bucket["pending_count"] += 1

        assignees = row.get("assignees") or []
        if not assignees:
            assignees = [{"id": None, "name": "Sin asignar"}]
        for assignee in assignees:
            assignee_id = assignee.get("id")
            assignee_name = assignee.get("name") or "Sin asignar"
            assignee_key = (int(assignee_id) if assignee_id else None, assignee_name)
            assignee_bucket = assignee_buckets.setdefault(
                assignee_key,
                {
                    "assignee_id": int(assignee_id) if assignee_id else None,
                    "assignee_name": assignee_name,
                    "task_count": 0,
                    "pending_count": 0,
                },
            )
            assignee_bucket["task_count"] += 1
            if is_pending:
                assignee_bucket["pending_count"] += 1

    stage_breakdown = sorted(
        stage_buckets.values(),
        key=lambda item: (item["sequence"], item["stage_name"], item["stage_id"] or 0),
    )
    for item in stage_breakdown:
        item.pop("sequence", None)

    assignee_breakdown = sorted(
        assignee_buckets.values(),
        key=lambda item: (-item["task_count"], item["assignee_name"], item["assignee_id"] or 0),
    )
    top_pending_tasks = [
        {
            "id": row.get("id"),
            "name": row.get("name"),
            "stage_name": row.get("stage_name") or "Sin etapa",
            "assignees": [assignee.get("name") or "Sin asignar" for assignee in (row.get("assignees") or [])] or ["Sin asignar"],
        }
        for row in pending_rows[:TOP_PENDING_TASK_LIMIT]
    ]

    return (
        {
            "pending_count": pending_count,
            "stage_breakdown": stage_breakdown,
            "assignee_breakdown": assignee_breakdown,
            "top_pending_tasks": top_pending_tasks,
            "aggregation_complete": aggregation_complete,
            "aggregation_sample_size": aggregation_sample_size,
        },
        warnings,
    )


def _default_limit_for_level(detail_level: DetailLevel, settings: Settings) -> int:
    return min(DEFAULT_LIMIT_BY_LEVEL[detail_level], settings.default_limit)


def build_controlled_list_envelope(
    *,
    source: str,
    rows: list[dict[str, Any]],
    total_count: int,
    offset: int,
    limit: int,
    detail_level: DetailLevel,
    summary_fields: list[str],
    standard_fields: list[str],
    full_fields: list[str] | None = None,
    include_fields: list[str] | None = None,
    truncate_text: int | None = None,
    applied_defaults: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_fields = _field_set_for_level(
        detail_level=detail_level,
        summary_fields=summary_fields,
        standard_fields=standard_fields,
        full_fields=full_fields,
        include_fields=include_fields,
    )
    text_limit = _resolve_text_limit(detail_level, truncate_text)
    projected_rows = [_project_item(row, selected_fields, text_limit) for row in rows]

    max_items = min(limit, MAX_ITEMS_BY_LEVEL[detail_level])
    emitted_rows = projected_rows[:max_items]
    truncated = len(projected_rows) > len(emitted_rows)
    char_budget = CHAR_BUDGET_BY_LEVEL[detail_level]
    while len(emitted_rows) > 1 and len(dumps_text(emitted_rows)) > char_budget:
        emitted_rows = emitted_rows[:-1]
        truncated = True

    if projected_rows and not emitted_rows:
        emitted_rows = projected_rows[:1]
        truncated = True

    final_truncated = truncated or total_count > offset + len(emitted_rows)
    merged_summary = {
        "detail_level": detail_level,
        "returned_fields": selected_fields,
        "text_truncation_limit": text_limit,
    }
    if summary:
        merged_summary.update(summary)
    return build_envelope(
        source=source,
        items=emitted_rows,
        total_count=total_count,
        limit=limit,
        offset=offset,
        applied_defaults=applied_defaults,
        warnings=warnings,
        summary=merged_summary,
        truncated=final_truncated,
    )


def _string_query_domain(fields: list[str], query: str) -> list[Any]:
    terms = [field for field in fields if field]
    if not terms:
        return []
    domain: list[Any] = ["|"] * max(len(terms) - 1, 0)
    for field in terms:
        domain.append((field, "ilike", query))
    return domain


@dataclass
class Runtime:
    settings: Settings
    odoo: OdooBackend
    biometric_ingest: BiometricIngestBackend
    branch_report: BranchAttendanceReportService

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_runtime(settings: Settings) -> Runtime:
    odoo = OdooBackend(
        url=settings.odoo_url,
        db=settings.odoo_db,
        login=settings.odoo_login,
        api_key=settings.odoo_api_key,
        locale=settings.odoo_locale,
        timeout_seconds=settings.odoo_timeout_seconds,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
    biometric_ingest = BiometricIngestBackend(
        dsn=settings.biometric_pg_dsn,
        statement_timeout_ms=settings.biometric_pg_statement_timeout_ms,
    )
    branch_report = BranchAttendanceReportService(odoo, settings.default_timezone)
    return Runtime(settings=settings, odoo=odoo, biometric_ingest=biometric_ingest, branch_report=branch_report)


def build_mcp_server(runtime: Runtime) -> FastMCP:
    settings = runtime.settings
    read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    public_url = urlparse(settings.public_base_url)
    public_host = public_url.netloc or public_url.path
    public_origin = f"{public_url.scheme or 'https'}://{public_host}" if public_host else settings.public_base_url
    mcp = FastMCP(
        name=settings.app_name,
        instructions=(
            "Read-only MCP server for Devlyn Odoo operations and Dahua attendance ingestion. "
            "Explore incrementally: start with count tools or narrow search tools, then paginate with `limit` and `cursor`. "
            "List-like tools default to `detail_level=summary` for token-efficient output; request `standard` or `full` only when necessary. "
            "All list tools return the standard envelope with `summary.total_count`, `next_cursor`, and `truncated`. "
            "Dates use ISO `YYYY-MM-DD`. Attendance and event tools default to the last 7 days when no date range is provided. "
            "Use detail tools after you already have an identifier. Never expect write or mutation capabilities."
        ),
        stateless_http=True,
        json_response=True,
        streamable_http_path=settings.mcp_mount_path,
        log_level=settings.log_level,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[
                public_host,
                f"{public_host}:443",
                "127.0.0.1:*",
                "localhost:*",
            ],
            allowed_origins=[
                public_origin,
                "http://127.0.0.1:*",
                "http://localhost:*",
            ],
        ),
    )

    @mcp.resource(
        "odoo-mcp://server/overview",
        name="server_overview",
        title="Server Overview",
        description="Human-readable server overview, data sources, defaults, authentication expectations, and scope boundaries.",
        mime_type="application/json",
    )
    def server_overview() -> str:
        payload = {
            "name": settings.app_name,
            "version": settings.app_version,
            "public_url": f"{settings.public_base_url}{settings.mcp_mount_path}",
            "authentication": {
                "primary_header": "X-API-Key",
                "bearer_fallback": True,
                "notes": "Provide the same connection token in either X-API-Key or Authorization: Bearer.",
            },
            "sources": {
                "odoo": ["hr.employee", "hr.attendance", "hr.biometric.event", "project.*", "helpdesk.ticket"],
                "biometric_ingest": ["raw_request", "normalized_event", "event_quarantine", "device_status"],
            },
            "defaults": {
                "default_limit": settings.default_limit,
                "max_limit": settings.max_limit,
                "default_window_days": settings.default_window_days,
            },
            "exploration_contract": {
                "standard_envelope_fields": STANDARD_ENVELOPE_FIELDS,
                "tool_errors": {
                    "shape": ["error_code", "message", "retryable", "suggested_arguments", "details"],
                    "surface": "tool-call results with `isError=true` expose structuredContent plus JSON text",
                },
                "pagination": {
                    "default_limit": settings.default_limit,
                    "max_limit": settings.max_limit,
                    "cursor_style": "opaque offset cursor",
                    "count_signal": "summary.total_count",
                    "next_page_signal": "next_cursor",
                },
                "detail_levels": ["summary", "standard", "full"],
                "dates": {
                    "format": "YYYY-MM-DD",
                    "default_window_days_for_attendance_and_events": settings.default_window_days,
                },
            },
            "out_of_scope": [
                "biometric.auth.*",
                "biometric.device",
                "biometric.policy",
                "auth-gateway",
                "Cognito",
                "Rekognition",
                "write operations",
            ],
        }
        return dumps_text(payload, indent=True)

    @mcp.resource(
        "odoo-mcp://server/tool-catalog",
        name="tool_catalog",
        title="Tool Catalog",
        description="Catalog of MCP tools grouped by domain with operational intent and cost guidance.",
        mime_type="application/json",
    )
    def tool_catalog() -> str:
        payload = {
            "recommended_flow": [
                {"goal": "understand server scope", "tools_or_resources": ["describe_server_capabilities", "odoo-mcp://server/usage-guide"]},
                {"goal": "estimate scope before fetching rows", "tools_or_resources": ["count_employees", "count_attendance_records", "count_hr_biometric_events", "count_dahua_normalized_events", "count_helpdesk_tickets"]},
                {"goal": "paginate through operational data", "tools_or_resources": ["search_employees", "search_attendance_records", "search_hr_biometric_events", "search_dahua_normalized_events"]},
                {"goal": "fetch one known record", "tools_or_resources": ["get_employee_by_id", "get_attendance_record_by_id", "get_hr_biometric_event_by_id", "get_dahua_normalized_event_by_id", "get_task_by_id", "get_helpdesk_ticket_by_id"]},
            ],
            "domains": {
                "employees": {"count": "count_employees", "search": "search_employees", "detail": "get_employee_by_id", "cost": "low"},
                "attendance": {
                    "count": "count_attendance_records",
                    "search": "search_attendance_records",
                    "detail": "get_attendance_record_by_id",
                    "summary": "get_employee_attendance_summary",
                    "report": "get_branch_attendance_report",
                    "cost": "medium_to_high",
                },
                "hr_biometric_events": {
                    "count": "count_hr_biometric_events",
                    "search": "search_hr_biometric_events",
                    "detail": "get_hr_biometric_event_by_id",
                    "cost": "medium",
                },
                "dahua": {
                    "normalized_count": "count_dahua_normalized_events",
                    "normalized_search": "search_dahua_normalized_events",
                    "normalized_detail": "get_dahua_normalized_event_by_id",
                    "raw_search": "search_dahua_raw_requests",
                    "quarantine_search": "search_dahua_quarantine_events",
                    "device_status": "get_dahua_device_status",
                    "cost": "low_to_medium",
                },
                "odoo_ops": {
                    "catalogs": "get_devlyn_catalogs",
                    "projects": "search_projects (accent-tolerant query matching)",
                    "tasks": "search_tasks (summary adds pending_count, stage_breakdown, assignee_breakdown, top_pending_tasks)",
                    "task_detail": "get_task_by_id",
                    "helpdesk_count": "count_helpdesk_tickets",
                    "helpdesk_search": "search_helpdesk_tickets",
                    "helpdesk_detail": "get_helpdesk_ticket_by_id",
                    "users": "search_users",
                    "contacts": "search_contacts",
                },
            },
        }
        return dumps_text(payload, indent=True)

    @mcp.resource(
        "odoo-mcp://server/usage-guide",
        name="usage_guide",
        title="Usage Guide",
        description="Practical guide for LLMs and operators: how to estimate scope, page through data, and choose the right tool sequence.",
        mime_type="application/json",
    )
    def usage_guide() -> str:
        payload = {
            "recommended_entrypoints": ["describe_server_capabilities", "odoo-mcp://server/tool-catalog", "odoo-mcp://server/filter-reference"],
            "patterns": [
                {
                    "goal": "find one employee and inspect attendance",
                    "steps": ["count_employees", "search_employees(detail_level=summary)", "get_employee_by_id", "count_attendance_records", "search_attendance_records(detail_level=summary)"],
                },
                {
                    "goal": "review Dahua ingestion issues",
                    "steps": ["count_dahua_normalized_events", "search_dahua_normalized_events(detail_level=summary)", "search_dahua_quarantine_events(detail_level=summary)", "get_dahua_device_status(detail_level=summary)"],
                },
                {
                    "goal": "run the Devlyn branch attendance report",
                    "steps": ["get_devlyn_catalogs(detail_level=summary)", "get_branch_attendance_report(detail_level=summary)"],
                },
                {
                    "goal": "find tasks in a project with assignees and stage",
                    "steps": ["search_projects(query='biometricos', detail_level=summary)", "search_tasks(project_ids=[project_id], detail_level=summary)"],
                },
            ],
            "rules": {
                "pagination": PAGINATION_DESCRIPTION,
                "envelope": STANDARD_ENVELOPE_DESCRIPTION,
                "dates": "Use ISO `YYYY-MM-DD`. Attendance and event tools default to the last 7 days if omitted.",
                "detail_lookup": DETAIL_DESCRIPTION,
                "detail_level": DETAIL_LEVEL_DESCRIPTION,
                "errors": "Tool failures return MCP `isError=true` with structured `error_code`, `message`, `retryable`, `suggested_arguments`, and `details`.",
            },
        }
        return dumps_text(payload, indent=True)

    @mcp.resource(
        "odoo-mcp://server/response-envelope",
        name="response_envelope_reference",
        title="Response Envelope Reference",
        description="Reference for the shared response shape returned by this MCP server.",
        mime_type="application/json",
    )
    def response_envelope_reference() -> str:
        payload = {
            "fields": {
                "source": "Backend that produced the data: `odoo`, `biometric_ingest`, or `hybrid`.",
                "summary": "Aggregates and counts. Search tools expose `summary.total_count`; count tools expose `summary.matched_count`.",
                "items": "Page of records, aggregated rows, or a single record.",
                "next_cursor": "Opaque token for the next page, or null when exhausted.",
                "applied_defaults": "Defaults applied automatically, such as inferred date windows.",
                "warnings": "Non-fatal issues such as `not_found`.",
                "truncated": "True when the response is intentionally compacted and more matching data remains or rows were clipped for size.",
            },
            "patterns": {
                "search_tools": {"items": "many", "count_signal": "summary.total_count", "pagination_signal": "next_cursor"},
                "count_tools": {"items": "empty", "count_signal": "summary.matched_count", "pagination_signal": None},
                "detail_tools": {"items": "zero_or_one", "count_signal": "summary.found", "pagination_signal": None},
                "tool_errors": {"isError": True, "fields": ["error_code", "message", "retryable", "suggested_arguments", "details"]},
            },
        }
        return dumps_text(payload, indent=True)

    @mcp.resource(
        "odoo-mcp://server/filter-reference",
        name="filter_reference",
        title="Filter Reference",
        description="Central reference for shared filter semantics, enum values, date behavior, and pagination defaults.",
        mime_type="application/json",
    )
    def filter_reference() -> str:
        payload = {
            "shared_filters": {
                "limit": {"default": settings.default_limit, "max": settings.max_limit},
                "cursor": "Opaque pagination cursor returned as `next_cursor`.",
                "detail_level": ["summary", "standard", "full"],
                "include_fields": "Optional list of extra top-level fields to add to compact row shapes when supported.",
                "truncate_text": "Optional max characters for strings. Use null or values <= 0 to disable truncation.",
                "date_from": "Inclusive ISO date `YYYY-MM-DD`.",
                "date_to": "Inclusive ISO date `YYYY-MM-DD`.",
            },
            "task_filters": {
                "project_ids": "Optional list of Odoo `project.project` ids.",
                "stage_ids": "Optional list of Odoo task stage ids.",
                "assignee_ids": "Optional list of Odoo `res.users` ids assigned through `project.task.user_ids`.",
            },
            "search_notes": {
                "project_query_matching": "Project queries use accent-folded, casefolded matching so `Biométricos` and `biometricos` resolve the same project.",
                "task_summary_aggregates": ["pending_count", "stage_breakdown", "assignee_breakdown", "top_pending_tasks"],
            },
            "enums": {
                "resolution_scope": ["all", "mapped_only", "sin_sucursal_only"],
                "sync_status": [
                    "pending",
                    "check_in_created",
                    "check_out_written",
                    "duplicate_ignored",
                    "employee_not_found",
                    "denied_ignored",
                    "after_close_review",
                    "error",
                ],
                "direction": ["entry", "exit", "unknown"],
                "device_status": ["online", "stale", "offline"],
            },
            "date_defaults": {
                "attendance_tools": settings.default_window_days,
                "event_tools": settings.default_window_days,
            },
        }
        return dumps_text(payload, indent=True)

    @mcp.resource(
        "odoo-mcp://schemas/{domain_name}",
        name="domain_schema",
        title="Domain Schema Reference",
        description="Schema-oriented resource that describes the key response fields for a supported MCP domain.",
        mime_type="application/json",
    )
    def domain_schema(domain_name: str) -> str:
        schemas = {
            "employees": {
                "primary_keys": ["id", "employee_number", "name"],
                "filters": ["query", "active", "cursor", "limit"],
                "count_tool": "count_employees",
                "search_tool": "search_employees",
                "detail_tool": "get_employee_by_id",
            },
            "attendance": {
                "primary_keys": ["id", "employee_id", "check_in", "check_out", "worked_hours"],
                "filters": ["date_from", "date_to", "employee_ids", "cursor", "limit"],
                "count_tool": "count_attendance_records",
                "search_tool": "search_attendance_records",
                "detail_tool": "get_attendance_record_by_id",
                "summary_tool": "get_employee_attendance_summary",
            },
            "dahua_normalized_events": {
                "primary_keys": ["id", "event_occurred_at_utc", "device_id_resolved", "user_id_on_device"],
                "filters": ["date_from", "date_to", "device_id", "user_id_on_device", "direction", "granted"],
                "count_tool": "count_dahua_normalized_events",
                "search_tool": "search_dahua_normalized_events",
                "detail_tool": "get_dahua_normalized_event_by_id",
                "enums": {"direction": ["entry", "exit", "unknown"]},
            },
            "branch_report": {
                "primary_keys": ["report_date", "employee_id", "center_code", "branch_name"],
                "filters": [
                    "date_from",
                    "date_to",
                    "employee_ids",
                    "resolution_scope",
                    "region_ids",
                    "zone_ids",
                    "district_ids",
                    "branch_ids",
                    "format_ids",
                    "status_ids",
                    "optical_level_ids",
                ],
                "search_tool": "get_branch_attendance_report",
                "enums": {"resolution_scope": ["all", "mapped_only", "sin_sucursal_only"]},
            },
        }
        payload = schemas.get(domain_name, {"error": "unknown_domain"})
        return dumps_text(payload, indent=True)

    @mcp.tool(
        name="describe_server_capabilities",
        title="Describe Server Capabilities",
        description=(
            "Explain this MCP server in plain operational language: data sources, read-only guarantees, default limits, "
            "default time windows, authentication conventions, and the domains supported in production."
        ),
        annotations=read_only,
    )
    def describe_server_capabilities() -> dict[str, Any]:
        return {
            "source": "hybrid",
            "summary": {
                "name": settings.app_name,
                "version": settings.app_version,
                "transport": "MCP streamable-http",
                "read_only": True,
                "default_limit": settings.default_limit,
                "max_limit": settings.max_limit,
                "default_window_days": settings.default_window_days,
            },
            "items": [
                {
                    "public_url": f"{settings.public_base_url}{settings.mcp_mount_path}",
                    "authentication": ["X-API-Key", "Authorization: Bearer"],
                    "data_sources": ["Odoo XML-RPC", "PostgreSQL biometric_ingest"],
                    "major_domains": [
                        "employees",
                        "attendance",
                        "hr.biometric.event",
                        "Devlyn branch attendance reporting",
                        "Dahua ingestion events",
                        "projects",
                        "tasks",
                        "helpdesk",
                        "users",
                        "contacts",
                    ],
                    "exploration_pattern": "count -> search -> detail",
                    "response_envelope": STANDARD_ENVELOPE_FIELDS,
                }
            ],
            "next_cursor": None,
            "applied_defaults": {},
            "warnings": [],
        }

    @mcp.tool(
        name="count_employees",
        title="Count Employees",
        description=(
            "Count matching Odoo `hr.employee` records before fetching pages. Supports the same `query` and `active` filters "
            "as `search_employees`, is intended as the first step for broad lookups, and returns no rows in `items`; "
            "read `summary.matched_count`. Cost: low."
        ),
        annotations=read_only,
    )
    async def count_employees(query: str | None = None, active: bool = True):
        model = "hr.employee"
        field_map = runtime.odoo.fields_get(model)
        domain: list[Any] = []
        if "active" in field_map:
            domain.append(("active", "=", bool(active)))
        if query:
            query = query.strip()
            query_fields = [field for field in ["name"] if field in field_map]
            if query_fields:
                query_domain = _string_query_domain(query_fields, query)
                if query.isdigit() and "employee_number" in field_map:
                    query_domain = ["|", ("employee_number", "=", int(query)), *query_domain]
                domain.extend(query_domain)
        matched_count = await asyncio.to_thread(runtime.odoo.search_count, model, domain)
        return build_count_result(source="odoo", matched_count=matched_count)

    @mcp.tool(
        name="search_employees",
        title="Search Employees",
        description=(
            "Read-only search over Odoo `hr.employee` for attendance and operational lookups. Supports free-text matching "
            "on employee number and name, returns business identifiers first, and paginates with `limit` plus `cursor`. "
            "Default output uses `detail_level=summary`; request `standard` or `full` only when needed. Read "
            "`summary.total_count` and `next_cursor` before paging further. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_employees(
        query: str | None = None,
        active: bool = True,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        model = "hr.employee"
        standard_fields = runtime.odoo.existing_fields(
            model,
            ["id", "name", "employee_number", "company_id", "parent_id", "user_id", "active"],
        )
        domain: list[Any] = []
        if "active" in runtime.odoo.fields_get(model):
            domain.append(("active", "=", bool(active)))
        if query:
            query = query.strip()
            query_fields = [field for field in ["name"] if field in standard_fields]
            if query_fields:
                query_domain = _string_query_domain(query_fields, query)
                if query.isdigit() and "employee_number" in standard_fields:
                    query_domain = ["|", ("employee_number", "=", int(query)), *query_domain]
                domain.extend(query_domain)
        total_count = await asyncio.to_thread(runtime.odoo.search_count, model, domain)
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            model,
            domain,
            fields=standard_fields,
            limit=limit_value,
            offset=offset,
            order="employee_number asc, name asc",
        )
        return build_controlled_list_envelope(
            source="odoo",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[field for field in ["id", "employee_number", "name", "active"] if field in standard_fields],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
        )

    @mcp.tool(
        name="get_employee_by_id",
        title="Get Employee By ID",
        description=(
            "Read-only detail lookup over Odoo `hr.employee` by numeric id. Use after `search_employees` when you already "
            "have a record identifier. Returns one item when found or `warnings=['not_found']` when missing. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_employee_by_id(employee_id: int):
        model = "hr.employee"
        fields = runtime.odoo.existing_fields(
            model,
            ["id", "name", "employee_number", "company_id", "parent_id", "user_id", "active"],
        )
        rows = await asyncio.to_thread(runtime.odoo.read, model, [int(employee_id)], fields)
        item = rows[0] if rows else None
        warnings = [] if item is not None else ["not_found"]
        return build_single_record_result(
            source="odoo",
            item=item,
            warnings=warnings,
            summary={"model": model, "requested_id": int(employee_id)},
        )

    @mcp.tool(
        name="count_attendance_records",
        title="Count Attendance Records",
        description=(
            "Count matching Odoo `hr.attendance` rows before fetching pages. Supports the same date and employee filters as "
            "`search_attendance_records`, defaults to the last 7 days when no date range is provided, and returns no rows in "
            "`items`; read `summary.matched_count`. This count covers raw attendance rows only; if you need branch, region, "
            "district, format, status, or optical level context, discover ids with `get_devlyn_catalogs` and query "
            "`get_branch_attendance_report` instead. Cost: low."
        ),
        annotations=read_only,
    )
    async def count_attendance_records(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})
        timezone_name = await asyncio.to_thread(runtime.odoo.get_timezone_name, settings.default_timezone)
        start_utc, end_utc = await asyncio.to_thread(
            utc_bounds_for_local_dates,
            start,
            end,
            timezone_name,
            settings.default_timezone,
        )
        domain: list[Any] = [("check_in", ">=", start_utc), ("check_in", "<", end_utc)]
        if employee_ids:
            domain.append(("employee_id", "in", [int(item) for item in employee_ids]))
        matched_count = await asyncio.to_thread(runtime.odoo.search_count, "hr.attendance", domain)
        return build_count_result(
            source="odoo",
            matched_count=matched_count,
            applied_defaults=applied_defaults,
            summary={"timezone_name": timezone_name},
        )

    @mcp.tool(
        name="search_attendance_records",
        title="Search Attendance Records",
        description=(
            "Read-only search over Odoo `hr.attendance`. Defaults to the last 7 days when no range is provided, supports "
            "employee filtering, and paginates with `limit` plus `cursor`. `check_in` and `check_out` are returned in the "
            "operational timezone declared in `summary.timezone_name`, serialized as ISO 8601 with offset. Default output "
            "uses `detail_level=summary`; request `standard` or `full` only when needed. This tool returns raw attendance "
            "rows and does not include branch/region/district/format/status/optical-level hierarchy; for that use "
            "`get_devlyn_catalogs` followed by `get_branch_attendance_report`. Cost: medium."
        ),
        annotations=read_only,
    )
    async def search_attendance_records(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})

        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        timezone_name = await asyncio.to_thread(runtime.odoo.get_timezone_name, settings.default_timezone)
        start_utc, end_utc = await asyncio.to_thread(
            utc_bounds_for_local_dates,
            start,
            end,
            timezone_name,
            settings.default_timezone,
        )
        domain: list[Any] = [("check_in", ">=", start_utc), ("check_in", "<", end_utc)]
        if employee_ids:
            domain.append(("employee_id", "in", [int(item) for item in employee_ids]))
        standard_fields = runtime.odoo.existing_fields(
            "hr.attendance",
            [
                "id",
                "employee_id",
                "check_in",
                "check_out",
                "worked_hours",
                "biometric_source",
                "biometric_inference_mode",
                "biometric_auto_closed",
                "biometric_auto_close_reason",
                "biometric_checkin_event_id",
                "biometric_checkout_event_id",
            ],
        )
        total_count = await asyncio.to_thread(runtime.odoo.search_count, "hr.attendance", domain)
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            "hr.attendance",
            domain,
            fields=standard_fields,
            limit=limit_value,
            offset=offset,
            order="check_in desc, id desc",
        )
        rows = _format_timestamp_fields(
            rows,
            field_names=["check_in", "check_out"],
            timezone_name=timezone_name,
            fallback_timezone=settings.default_timezone,
        )
        return build_controlled_list_envelope(
            source="odoo",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[field for field in ["id", "employee_id", "check_in", "check_out", "worked_hours"] if field in standard_fields],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
            summary={"timezone_name": timezone_name, "timestamp_format": "iso8601_offset"},
        )

    @mcp.tool(
        name="get_attendance_record_by_id",
        title="Get Attendance Record By ID",
        description=(
            "Read-only detail lookup over Odoo `hr.attendance` by numeric id. Use after `search_attendance_records` when you "
            "already have a record identifier. Returns one item when found or `warnings=['not_found']` when missing. Like "
            "`search_attendance_records`, this exposes the raw attendance row only; branch/region/district/format/status/"
            "optical-level context lives in `get_branch_attendance_report`. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_attendance_record_by_id(attendance_id: int):
        model = "hr.attendance"
        timezone_name = await asyncio.to_thread(runtime.odoo.get_timezone_name, settings.default_timezone)
        fields = runtime.odoo.existing_fields(
            model,
            [
                "id",
                "employee_id",
                "check_in",
                "check_out",
                "worked_hours",
                "biometric_source",
                "biometric_inference_mode",
                "biometric_auto_closed",
                "biometric_auto_close_reason",
                "biometric_checkin_event_id",
                "biometric_checkout_event_id",
            ],
        )
        rows = await asyncio.to_thread(runtime.odoo.read, model, [int(attendance_id)], fields)
        rows = _format_timestamp_fields(
            rows,
            field_names=["check_in", "check_out"],
            timezone_name=timezone_name,
            fallback_timezone=settings.default_timezone,
        )
        item = rows[0] if rows else None
        warnings = [] if item is not None else ["not_found"]
        return build_single_record_result(
            source="odoo",
            item=item,
            warnings=warnings,
            summary={
                "model": model,
                "requested_id": int(attendance_id),
                "timezone_name": timezone_name,
                "timestamp_format": "iso8601_offset",
            },
        )

    @mcp.tool(
        name="get_employee_attendance_summary",
        title="Get Employee Attendance Summary",
        description=(
            "Summarize biometric attendance per employee across a date range. Defaults to the last 7 days and returns "
            "aggregated worked hours, open segments, number of attendance rows, and first/last observed times. Default "
            "output uses `detail_level=summary` with top rows plus pagination, not the full aggregated table. This summary "
            "stays employee-centric and does not add branch/region/district/format/status/optical-level hierarchy; use "
            "`get_devlyn_catalogs` plus `get_branch_attendance_report` when you need that operational structure. Cost: medium."
        ),
        annotations=read_only,
    )
    async def get_employee_attendance_summary(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        timezone_name = await asyncio.to_thread(runtime.odoo.get_timezone_name, settings.default_timezone)
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})

        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        domain: list[Any] = [("summary_date", ">=", start.isoformat()), ("summary_date", "<=", end.isoformat())]
        if employee_ids:
            domain.append(("employee_id", "in", [int(item) for item in employee_ids]))
        fields = runtime.odoo.existing_fields(
            "biometric.attendance.summary",
            [
                "id",
                "summary_date",
                "employee_id",
                "user_id",
                "login",
                "first_check_in",
                "last_check_out",
                "total_worked_hours",
                "segments",
                "open_segments",
            ],
        )
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            "biometric.attendance.summary",
            domain,
            fields=fields,
            limit=20000,
            offset=0,
            order="summary_date desc, employee_id asc",
        )
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            employee = row.get("employee_id") or {}
            employee_id = employee.get("id")
            if not employee_id:
                continue
            bucket = grouped.setdefault(
                int(employee_id),
                {
                    "employee_id": int(employee_id),
                    "employee_name": employee.get("display_name"),
                    "user_id": (row.get("user_id") or {}).get("id"),
                    "login": row.get("login"),
                    "days": 0,
                    "total_worked_hours": 0.0,
                    "segments": 0,
                    "open_segments": 0,
                    "first_check_in": None,
                    "last_check_out": None,
                },
            )
            bucket["days"] += 1
            bucket["total_worked_hours"] += float(row.get("total_worked_hours") or 0.0)
            bucket["segments"] += int(row.get("segments") or 0)
            bucket["open_segments"] += int(row.get("open_segments") or 0)
            first_check_in = row.get("first_check_in")
            last_check_out = row.get("last_check_out")
            if first_check_in and (bucket["first_check_in"] is None or first_check_in < bucket["first_check_in"]):
                bucket["first_check_in"] = first_check_in
            if last_check_out and (bucket["last_check_out"] is None or last_check_out > bucket["last_check_out"]):
                bucket["last_check_out"] = last_check_out
        items = list(grouped.values())
        total_count = len(items)
        if detail_level == "summary":
            items.sort(key=lambda item: (-item["total_worked_hours"], -(item["days"]), item["employee_name"] or "", item["employee_id"]))
        else:
            items.sort(key=lambda item: (item["employee_name"] or "", item["employee_id"]))
        window = items[offset : offset + limit_value]
        window = _format_timestamp_fields(
            window,
            field_names=["first_check_in", "last_check_out"],
            timezone_name=timezone_name,
            fallback_timezone=settings.default_timezone,
        )
        total_hours = round(sum(float(item["total_worked_hours"]) for item in items), 2)
        total_segments = sum(int(item["segments"]) for item in items)
        total_open_segments = sum(int(item["open_segments"]) for item in items)
        return build_controlled_list_envelope(
            source="odoo",
            rows=window,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=["employee_id", "employee_name", "days", "total_worked_hours", "open_segments"],
            standard_fields=[
                "employee_id",
                "employee_name",
                "user_id",
                "login",
                "days",
                "total_worked_hours",
                "segments",
                "open_segments",
                "first_check_in",
                "last_check_out",
            ],
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
            summary={
                "employee_count": total_count,
                "total_worked_hours": total_hours,
                "total_segments": total_segments,
                "total_open_segments": total_open_segments,
                "ordering": "top_worked_hours_desc" if detail_level == "summary" else "employee_name_asc",
                "timezone_name": timezone_name,
                "timestamp_format": "iso8601_offset",
            },
        )

    @mcp.tool(
        name="count_hr_biometric_events",
        title="Count HR Biometric Events",
        description=(
            "Count matching synchronized Dahua events stored in Odoo `hr.biometric.event`. Supports the same date, employee, "
            "device, user, and `sync_status` filters as `search_hr_biometric_events`, defaults to the last 7 days, and "
            "returns no rows in `items`; read `summary.matched_count`. Cost: low."
        ),
        annotations=read_only,
    )
    async def count_hr_biometric_events(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
        device_id_resolved: str | None = None,
        user_id_on_device: str | None = None,
        sync_status: SyncStatus | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})
        domain: list[Any] = [
            ("event_occurred_at_utc", ">=", f"{start.isoformat()} 00:00:00"),
            ("event_occurred_at_utc", "<=", f"{end.isoformat()} 23:59:59"),
        ]
        if employee_ids:
            domain.append(("employee_id", "in", [int(item) for item in employee_ids]))
        if device_id_resolved:
            domain.append(("device_id_resolved", "ilike", device_id_resolved.strip()))
        if user_id_on_device:
            domain.append(("user_id_on_device", "ilike", user_id_on_device.strip()))
        if sync_status:
            domain.append(("sync_status", "=", sync_status))
        matched_count = await asyncio.to_thread(runtime.odoo.search_count, "hr.biometric.event", domain)
        return build_count_result(
            source="odoo",
            matched_count=matched_count,
            applied_defaults=applied_defaults,
            summary={"timezone_name": "UTC", "timestamp_format": "iso8601_offset"},
        )

    @mcp.tool(
        name="search_hr_biometric_events",
        title="Search HR Biometric Events",
        description=(
            "Read-only search over synchronized Dahua attendance events stored in Odoo `hr.biometric.event`. "
            "Defaults to the last 7 days, supports filters by employee, device, user, and `sync_status`, and paginates "
            "with `limit` plus `cursor`. `event_occurred_at_utc` remains UTC and is serialized as ISO 8601 with offset; "
            "read `summary.timezone_name` for the timestamp reference. Default output uses `detail_level=summary`; request "
            "`standard` or `full` only when needed. Cost: medium."
        ),
        annotations=read_only,
    )
    async def search_hr_biometric_events(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
        device_id_resolved: str | None = None,
        user_id_on_device: str | None = None,
        sync_status: SyncStatus | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        domain: list[Any] = [
            ("event_occurred_at_utc", ">=", f"{start.isoformat()} 00:00:00"),
            ("event_occurred_at_utc", "<=", f"{end.isoformat()} 23:59:59"),
        ]
        if employee_ids:
            domain.append(("employee_id", "in", [int(item) for item in employee_ids]))
        if device_id_resolved:
            domain.append(("device_id_resolved", "ilike", device_id_resolved.strip()))
        if user_id_on_device:
            domain.append(("user_id_on_device", "ilike", user_id_on_device.strip()))
        if sync_status:
            domain.append(("sync_status", "=", sync_status))
        standard_fields = runtime.odoo.existing_fields(
            "hr.biometric.event",
            [
                "id",
                "normalized_event_id",
                "event_kind",
                "event_occurred_at_utc",
                "event_local_date",
                "event_local_display",
                "user_id_on_device",
                "card_name",
                "employee_id",
                "device_id_resolved",
                "identity_resolution",
                "door_name",
                "reader_id",
                "direction_raw",
                "granted_state",
                "sync_status",
                "attendance_action",
                "attendance_id",
                "inference_mode",
                "attendance_auto_closed",
                "auto_close_reason",
                "message",
            ],
        )
        total_count = await asyncio.to_thread(runtime.odoo.search_count, "hr.biometric.event", domain)
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            "hr.biometric.event",
            domain,
            fields=standard_fields,
            limit=limit_value,
            offset=offset,
            order="event_occurred_at_utc desc, id desc",
        )
        rows = _format_timestamp_fields(
            rows,
            field_names=["event_occurred_at_utc"],
            timezone_name="UTC",
            fallback_timezone=settings.default_timezone,
        )
        return build_controlled_list_envelope(
            source="odoo",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[
                field
                for field in [
                    "id",
                    "event_occurred_at_utc",
                    "employee_id",
                    "user_id_on_device",
                    "device_id_resolved",
                    "sync_status",
                    "attendance_action",
                ]
                if field in standard_fields
            ],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
            summary={"timezone_name": "UTC", "timestamp_format": "iso8601_offset"},
        )

    @mcp.tool(
        name="get_hr_biometric_event_by_id",
        title="Get HR Biometric Event By ID",
        description=(
            "Read-only detail lookup over Odoo `hr.biometric.event` by numeric id. Use after `search_hr_biometric_events` "
            "when you already have a record identifier. Returns one item when found or `warnings=['not_found']` when missing. "
            "Cost: low."
        ),
        annotations=read_only,
    )
    async def get_hr_biometric_event_by_id(event_id: int):
        model = "hr.biometric.event"
        fields = runtime.odoo.existing_fields(
            model,
            [
                "id",
                "normalized_event_id",
                "event_kind",
                "event_occurred_at_utc",
                "event_local_date",
                "event_local_display",
                "user_id_on_device",
                "card_name",
                "employee_id",
                "device_id_resolved",
                "identity_resolution",
                "door_name",
                "reader_id",
                "direction_raw",
                "granted_state",
                "sync_status",
                "attendance_action",
                "attendance_id",
                "inference_mode",
                "attendance_auto_closed",
                "auto_close_reason",
                "message",
            ],
        )
        rows = await asyncio.to_thread(runtime.odoo.read, model, [int(event_id)], fields)
        rows = _format_timestamp_fields(
            rows,
            field_names=["event_occurred_at_utc"],
            timezone_name="UTC",
            fallback_timezone=settings.default_timezone,
        )
        item = rows[0] if rows else None
        warnings = [] if item is not None else ["not_found"]
        return build_single_record_result(
            source="odoo",
            item=item,
            warnings=warnings,
            summary={
                "model": model,
                "requested_id": int(event_id),
                "timezone_name": "UTC",
                "timestamp_format": "iso8601_offset",
            },
        )

    @mcp.tool(
        name="get_devlyn_catalogs",
        title="Get Devlyn Catalogs",
        description=(
            "Read-only access to Devlyn attendance reporting catalogs stored in Odoo. Returns active regions, zones, districts, "
            "formats, statuses, optical levels, and branches used by the branch attendance report. This is the deliberate "
            "one-shot catalog tool in the server: use it to discover valid ids before calling `get_branch_attendance_report`. "
            "Default output uses `detail_level=summary` with counts plus small samples per catalog. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_devlyn_catalogs(
        detail_level: DetailLevel = "summary",
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        catalogs = await asyncio.to_thread(runtime.odoo.get_devlyn_catalogs)
        total_count = sum(len(items) for items in catalogs.values())
        per_catalog_limit = {"summary": 3, "standard": 10, "full": 5000}[detail_level]
        text_limit = _resolve_text_limit(detail_level, truncate_text)
        catalog_counts = {name: len(items) for name, items in catalogs.items()}
        catalog_samples: dict[str, list[dict[str, Any]]] = {}
        any_truncated = False
        for name, items in catalogs.items():
            if items:
                default_fields = list(items[0].keys())
            else:
                default_fields = []
            selected_fields = _merge_requested_fields(default_fields, include_fields)
            sample_rows = items[:per_catalog_limit]
            catalog_samples[name] = [_project_item(row, selected_fields, text_limit) for row in sample_rows]
            if len(items) > len(sample_rows):
                any_truncated = True
        return build_envelope(
            source="odoo",
            items=[
                {
                    "catalog_counts": catalog_counts,
                    "catalog_samples": catalog_samples,
                }
            ],
            total_count=1,
            limit=1,
            offset=0,
            summary={
                "catalog_item_count": total_count,
                "detail_level": detail_level,
                "per_catalog_limit": per_catalog_limit,
                "returned_fields": include_fields or "default_catalog_fields",
            },
            truncated=any_truncated,
        )

    @mcp.tool(
        name="get_branch_attendance_report",
        title="Get Branch Attendance Report",
        description=(
            "Compute the Devlyn branch attendance report directly from Odoo data without creating transient viewers or wizards. "
            "It reproduces the production report logic: biometric_source=biometric_v1, timezone from sync config, grouping by employee/date, "
            "branch derivation from resolved device IDs, and explicit SIN_SUCURSAL classification. Use `get_devlyn_catalogs` "
            "first to discover valid filter ids, keep date ranges short, and paginate with `limit` plus `cursor` when needed. "
            "Default output uses `detail_level=summary` with compact operational rows. Cost: high."
        ),
        annotations=read_only,
    )
    async def get_branch_attendance_report(
        date_from: str | None = None,
        date_to: str | None = None,
        employee_ids: list[int] | None = None,
        resolution_scope: ResolutionScope = "all",
        region_ids: list[int] | None = None,
        zone_ids: list[int] | None = None,
        district_ids: list[int] | None = None,
        branch_ids: list[int] | None = None,
        format_ids: list[int] | None = None,
        status_ids: list[int] | None = None,
        optical_level_ids: list[int] | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        rows, timezone_name = await asyncio.to_thread(
            runtime.branch_report.build_rows,
            date_from=start,
            date_to=end,
            employee_ids=_coerce_relation_ids(employee_ids),
            resolution_scope=resolution_scope,
            region_ids=_coerce_relation_ids(region_ids),
            zone_ids=_coerce_relation_ids(zone_ids),
            district_ids=_coerce_relation_ids(district_ids),
            branch_ids=_coerce_relation_ids(branch_ids),
            format_ids=_coerce_relation_ids(format_ids),
            status_ids=_coerce_relation_ids(status_ids),
            optical_level_ids=_coerce_relation_ids(optical_level_ids),
        )
        total_count = len(rows)
        paged = rows[offset : offset + limit_value]
        mapped_rows = sum(1 for row in rows if row.get("branch_id"))
        return build_controlled_list_envelope(
            source="hybrid",
            rows=paged,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[
                "report_date",
                "employee_id",
                "employee_name",
                "center_code",
                "branch_name",
                "worked_hours",
                "worked_hours_display",
            ],
            standard_fields=list(paged[0].keys()) if paged else [
                "report_date",
                "employee_id",
                "employee_name",
                "center_code",
                "branch_name",
                "worked_hours",
                "attendance_status",
            ],
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
            summary={
                "timezone_name": timezone_name,
                "mapped_rows": mapped_rows,
                "unmapped_rows": total_count - mapped_rows,
                "resolution_scope": resolution_scope,
            },
        )

    def _postgres_date_filters(
        *,
        date_from: str | None,
        date_to: str | None,
        column_name: str,
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        applied_defaults: dict[str, Any] = {}
        start = parse_date_or_none(date_from)
        end = parse_date_or_none(date_to)
        if start is None or end is None:
            default_start, default_end = default_date_range(settings.default_window_days)
            start = start or default_start
            end = end or default_end
            applied_defaults.update({"date_from": start.isoformat(), "date_to": end.isoformat()})
        where = f"where {column_name} >= %(date_from)s and {column_name} < (%(date_to)s::date + interval '1 day')"
        params = {"date_from": start.isoformat(), "date_to": end.isoformat()}
        return applied_defaults, where, params

    @mcp.tool(
        name="search_dahua_raw_requests",
        title="Search Dahua Raw Requests",
        description=(
            "Read-only search over raw HTTP requests captured in PostgreSQL `biometric_ingest.raw_request`. "
            "Defaults to the last 7 days and is useful for low-level device troubleshooting and payload inspection. "
            "Default output uses `detail_level=summary`; request `standard` or `full` only when needed. Cost: medium."
        ),
        annotations=read_only,
    )
    async def search_dahua_raw_requests(
        date_from: str | None = None,
        date_to: str | None = None,
        event_kind_detected: str | None = None,
        device_id_hint: str | None = None,
        source_ip: str | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        applied_defaults, where_sql, params = _postgres_date_filters(
            date_from=date_from,
            date_to=date_to,
            column_name="received_at_utc",
        )
        filters = []
        if event_kind_detected:
            filters.append("event_kind_detected = %(event_kind_detected)s")
            params["event_kind_detected"] = event_kind_detected
        if device_id_hint:
            filters.append("device_id_hint ilike %(device_id_hint)s")
            params["device_id_hint"] = f"%{device_id_hint.strip()}%"
        if source_ip:
            filters.append("source_ip::text = %(source_ip)s")
            params["source_ip"] = source_ip.strip()
        if filters:
            where_sql = f"{where_sql} and " + " and ".join(filters)
        table = "raw_request"
        standard_fields = [
            "id",
            "received_at_utc",
            "ingest_id",
            "source_ip",
            "source_port",
            "listener_port",
            "method",
            "path",
            "query",
            "payload_hash",
            "event_kind_detected",
            "device_id_hint",
            "device_model_hint",
        ]
        total_count = await asyncio.to_thread(runtime.biometric_ingest.fetch_count, where_sql, params, table)
        rows = await asyncio.to_thread(
            runtime.biometric_ingest.fetch_rows,
            table=table,
            columns=standard_fields,
            where_sql=where_sql,
            params=params,
            order_by="received_at_utc desc, id desc",
            limit=limit_value,
            offset=offset,
        )
        return build_controlled_list_envelope(
            source="biometric_ingest",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=["id", "received_at_utc", "source_ip", "listener_port", "event_kind_detected", "device_id_hint"],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
        )

    @mcp.tool(
        name="count_dahua_normalized_events",
        title="Count Dahua Normalized Events",
        description=(
            "Count matching rows in PostgreSQL `biometric_ingest.normalized_event` before fetching pages. Supports the same "
            "filters as `search_dahua_normalized_events`, defaults to the last 7 days, and returns no rows in `items`; "
            "read `summary.matched_count`. Cost: low."
        ),
        annotations=read_only,
    )
    async def count_dahua_normalized_events(
        date_from: str | None = None,
        date_to: str | None = None,
        device_id: str | None = None,
        user_id_on_device: str | None = None,
        direction: DirectionFilter | None = None,
        granted: bool | None = None,
    ):
        applied_defaults, where_sql, params = _postgres_date_filters(
            date_from=date_from,
            date_to=date_to,
            column_name="event_occurred_at_utc",
        )
        filters = []
        if device_id:
            filters.append("device_id_resolved ilike %(device_id)s")
            params["device_id"] = f"%{device_id.strip()}%"
        if user_id_on_device:
            filters.append("user_id_on_device ilike %(user_id_on_device)s")
            params["user_id_on_device"] = f"%{user_id_on_device.strip()}%"
        if direction:
            filters.append("direction = %(direction)s")
            params["direction"] = direction
        if granted is not None:
            filters.append("granted = %(granted)s")
            params["granted"] = granted
        if filters:
            where_sql = f"{where_sql} and " + " and ".join(filters)
        matched_count = await asyncio.to_thread(runtime.biometric_ingest.fetch_count, where_sql, params, "normalized_event")
        return build_count_result(source="biometric_ingest", matched_count=matched_count, applied_defaults=applied_defaults)

    @mcp.tool(
        name="search_dahua_normalized_events",
        title="Search Dahua Normalized Events",
        description=(
            "Read-only search over normalized Dahua attendance events in PostgreSQL `biometric_ingest.normalized_event`. "
            "Defaults to the last 7 days, supports filters by device, user, direction, and granted state, and returns the "
            "canonical event timeline used by the attendance sync worker. Paginate with `limit` plus `cursor` and read "
            "`summary.total_count` before requesting more pages. Default output uses `detail_level=summary`. Cost: low to medium."
        ),
        annotations=read_only,
    )
    async def search_dahua_normalized_events(
        date_from: str | None = None,
        date_to: str | None = None,
        device_id: str | None = None,
        user_id_on_device: str | None = None,
        direction: DirectionFilter | None = None,
        granted: bool | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        applied_defaults, where_sql, params = _postgres_date_filters(
            date_from=date_from,
            date_to=date_to,
            column_name="event_occurred_at_utc",
        )
        filters = []
        if device_id:
            filters.append("device_id_resolved ilike %(device_id)s")
            params["device_id"] = f"%{device_id.strip()}%"
        if user_id_on_device:
            filters.append("user_id_on_device ilike %(user_id_on_device)s")
            params["user_id_on_device"] = f"%{user_id_on_device.strip()}%"
        if direction:
            filters.append("direction = %(direction)s")
            params["direction"] = direction
        if granted is not None:
            filters.append("granted = %(granted)s")
            params["granted"] = granted
        if filters:
            where_sql = f"{where_sql} and " + " and ".join(filters)
        table = "normalized_event"
        standard_fields = [
            "id",
            "raw_request_id",
            "raw_received_at_utc",
            "event_occurred_at_utc",
            "event_kind",
            "device_id_resolved",
            "source_ip",
            "listener_port",
            "user_id_on_device",
            "card_name",
            "door_name",
            "direction",
            "granted",
            "error_code",
            "reader_id",
            "identity_resolution",
            "created_at",
        ]
        total_count = await asyncio.to_thread(runtime.biometric_ingest.fetch_count, where_sql, params, table)
        rows = await asyncio.to_thread(
            runtime.biometric_ingest.fetch_rows,
            table=table,
            columns=standard_fields,
            where_sql=where_sql,
            params=params,
            order_by="event_occurred_at_utc desc, id desc",
            limit=limit_value,
            offset=offset,
        )
        return build_controlled_list_envelope(
            source="biometric_ingest",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[
                "id",
                "event_occurred_at_utc",
                "event_kind",
                "device_id_resolved",
                "user_id_on_device",
                "direction",
                "granted",
                "error_code",
            ],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
        )

    @mcp.tool(
        name="get_dahua_normalized_event_by_id",
        title="Get Dahua Normalized Event By ID",
        description=(
            "Read-only detail lookup over PostgreSQL `biometric_ingest.normalized_event` by numeric id. Use after "
            "`search_dahua_normalized_events` when you already have a record identifier. Returns one item when found or "
            "`warnings=['not_found']` when missing. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_dahua_normalized_event_by_id(event_id: int):
        rows = await asyncio.to_thread(
            runtime.biometric_ingest.fetch_rows,
            table="normalized_event",
            columns=[
                "id",
                "raw_request_id",
                "raw_received_at_utc",
                "event_occurred_at_utc",
                "event_kind",
                "device_id_resolved",
                "source_ip",
                "listener_port",
                "user_id_on_device",
                "card_name",
                "door_name",
                "direction",
                "granted",
                "error_code",
                "reader_id",
                "identity_resolution",
                "created_at",
            ],
            where_sql="where id = %(event_id)s",
            params={"event_id": int(event_id)},
            order_by="id asc",
            limit=1,
            offset=0,
        )
        item = rows[0] if rows else None
        warnings = [] if item is not None else ["not_found"]
        return build_single_record_result(
            source="biometric_ingest",
            item=item,
            warnings=warnings,
            summary={"table": "normalized_event", "requested_id": int(event_id)},
        )

    @mcp.tool(
        name="search_dahua_quarantine_events",
        title="Search Dahua Quarantine Events",
        description=(
            "Read-only search over `biometric_ingest.event_quarantine`, which contains raw Dahua requests that could not be "
            "normalized or were intentionally quarantined for review. Paginate with `limit` plus `cursor` and read "
            "`summary.total_count` before requesting more pages. Default output uses `detail_level=summary`. Cost: medium."
        ),
        annotations=read_only,
    )
    async def search_dahua_quarantine_events(
        date_from: str | None = None,
        date_to: str | None = None,
        reason: str | None = None,
        candidate_device_id: str | None = None,
        event_kind: str | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        applied_defaults, where_sql, params = _postgres_date_filters(
            date_from=date_from,
            date_to=date_to,
            column_name="created_at",
        )
        filters = []
        if reason:
            filters.append("reason = %(reason)s")
            params["reason"] = reason
        if candidate_device_id:
            filters.append("candidate_device_id ilike %(candidate_device_id)s")
            params["candidate_device_id"] = f"%{candidate_device_id.strip()}%"
        if event_kind:
            filters.append("event_kind = %(event_kind)s")
            params["event_kind"] = event_kind
        if filters:
            where_sql = f"{where_sql} and " + " and ".join(filters)
        table = "event_quarantine"
        standard_fields = [
            "id",
            "raw_request_id",
            "raw_received_at_utc",
            "source_ip",
            "listener_port",
            "payload_hash",
            "reason",
            "candidate_device_id",
            "event_kind",
            "created_at",
        ]
        total_count = await asyncio.to_thread(runtime.biometric_ingest.fetch_count, where_sql, params, table)
        rows = await asyncio.to_thread(
            runtime.biometric_ingest.fetch_rows,
            table=table,
            columns=standard_fields,
            where_sql=where_sql,
            params=params,
            order_by="created_at desc, id desc",
            limit=limit_value,
            offset=offset,
        )
        return build_controlled_list_envelope(
            source="biometric_ingest",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=["id", "raw_received_at_utc", "source_ip", "reason", "candidate_device_id", "event_kind", "created_at"],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            applied_defaults=applied_defaults,
        )

    @mcp.tool(
        name="get_dahua_device_status",
        title="Get Dahua Device Status",
        description=(
            "Read-only query over `biometric_ingest.device_status`. Returns the latest heartbeat and event state per Dahua device "
            "and is optimized for operational health checks. Filter by operational `status` when needed and paginate with "
            "`limit` plus `cursor`. Read `summary.total_count` before requesting more pages. Default output uses "
            "`detail_level=summary`. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_dahua_device_status(
        status: DeviceOperationalStatus | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        where_sql = ""
        params: dict[str, Any] = {}
        if status:
            where_sql = "where status = %(status)s"
            params["status"] = status
        table = "device_status"
        standard_fields = [
            "device_id",
            "last_seen_at",
            "last_heartbeat_at",
            "last_event_at",
            "last_event_kind",
            "status",
            "heartbeat_interval_seconds",
            "stale_since",
            "offline_since",
            "last_source_ip",
            "last_listener_port",
            "updated_at",
        ]
        total_count = await asyncio.to_thread(runtime.biometric_ingest.fetch_count, where_sql, params, table)
        rows = await asyncio.to_thread(
            runtime.biometric_ingest.fetch_rows,
            table=table,
            columns=standard_fields,
            where_sql=where_sql,
            params=params,
            order_by="device_id asc",
            limit=limit_value,
            offset=offset,
        )
        return build_controlled_list_envelope(
            source="biometric_ingest",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=["device_id", "status", "last_heartbeat_at", "last_event_at", "last_event_kind", "offline_since"],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
        )

    async def _search_odoo_model(
        *,
        model: str,
        query: str | None,
        detail_level: DetailLevel,
        limit: int | None,
        cursor: str | None,
        order: str,
        candidate_fields: list[str],
        summary_fields: list[str],
        search_fields: list[str],
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
        active: bool | None = None,
    ) -> dict[str, Any]:
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        standard_fields = runtime.odoo.existing_fields(model, candidate_fields)
        domain: list[Any] = []
        field_map = runtime.odoo.fields_get(model)
        if active is not None and "active" in field_map:
            domain.append(("active", "=", bool(active)))
        if query:
            usable_search_fields = [field for field in search_fields if field in field_map]
            if usable_search_fields:
                domain.extend(_string_query_domain(usable_search_fields, query.strip()))
        total_count = await asyncio.to_thread(runtime.odoo.search_count, model, domain)
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            model,
            domain,
            fields=standard_fields,
            limit=limit_value,
            offset=offset,
            order=order,
        )
        return build_controlled_list_envelope(
            source="odoo",
            rows=rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[field for field in summary_fields if field in standard_fields],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
        )

    @mcp.tool(
        name="search_projects",
        title="Search Projects",
        description=(
            "Read-only search over Odoo `project.project`, intended for operational context around attendance-related work. "
            "Project name matching is accent-tolerant for exploratory queries such as `Biométricos` and `biometricos`. "
            "Default output uses `detail_level=summary`. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_projects(
        query: str | None = None,
        active: bool = True,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        model = "project.project"
        standard_fields = runtime.odoo.existing_fields(model, ["id", "name", "display_name", "user_id", "company_id", "active"])
        if not query:
            return await _search_odoo_model(
                model=model,
                query=query,
                detail_level=detail_level,
                limit=limit,
                cursor=cursor,
                order="name asc",
                candidate_fields=standard_fields,
                summary_fields=["id", "name", "active"],
                search_fields=["name", "display_name"],
                include_fields=include_fields,
                truncate_text=truncate_text,
                active=active,
            )

        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        domain: list[Any] = []
        field_map = runtime.odoo.fields_get(model)
        if "active" in field_map:
            domain.append(("active", "=", bool(active)))
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            model,
            domain,
            fields=standard_fields,
            limit=5000,
            offset=0,
            order="name asc",
        )
        normalized_query = _fold_search_text(query)
        filtered_rows = [
            row
            for row in rows
            if normalized_query
            in " ".join(
                filter(
                    None,
                    [
                        _fold_search_text(str(row.get("name") or "")),
                        _fold_search_text(str(row.get("display_name") or "")),
                    ],
                )
            )
        ]
        paged_rows = filtered_rows[offset : offset + limit_value]
        return build_controlled_list_envelope(
            source="odoo",
            rows=paged_rows,
            total_count=len(filtered_rows),
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=[field for field in ["id", "name", "active"] if field in standard_fields],
            standard_fields=standard_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            summary={"query_normalized": normalized_query},
        )

    @mcp.tool(
        name="search_tasks",
        title="Search Tasks",
        description=(
            "Read-only search over Odoo `project.task` with direct project, stage, and assignee context. Supports filtering "
            "by `project_ids`, `stage_ids`, and `assignee_ids`, and the default `detail_level=summary` already returns "
            "resolved `assignees` plus flattened `project_name` and `stage_name` for operational follow-up. Summary mode "
            "also includes compact operational aggregates such as `pending_count`, `stage_breakdown`, and `assignee_breakdown`. "
            "Paginate with `limit` plus `cursor` and read `summary.total_count` before requesting more pages. Use "
            "`get_task_by_id` for one task. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_tasks(
        query: str | None = None,
        active: bool = True,
        project_ids: list[int] | None = None,
        stage_ids: list[int] | None = None,
        assignee_ids: list[int] | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        model = "project.task"
        limit_value = clamp_limit(limit, default=_default_limit_for_level(detail_level, settings), max_limit=settings.max_limit)
        offset = decode_offset_cursor(cursor)
        standard_fields = runtime.odoo.existing_fields(
            model,
            ["id", "name", "display_name", "project_id", "user_ids", "company_id", "active", "stage_id"],
        )
        domain: list[Any] = []
        field_map = runtime.odoo.fields_get(model)
        if "active" in field_map:
            domain.append(("active", "=", bool(active)))
        if query:
            usable_search_fields = [field for field in ["name", "display_name"] if field in field_map]
            if usable_search_fields:
                domain.extend(_string_query_domain(usable_search_fields, query.strip()))
        if project_ids and "project_id" in field_map:
            domain.append(("project_id", "in", [int(item) for item in project_ids]))
        if stage_ids and "stage_id" in field_map:
            domain.append(("stage_id", "in", [int(item) for item in stage_ids]))
        if assignee_ids and "user_ids" in field_map:
            domain.append(("user_ids", "in", [int(item) for item in assignee_ids]))

        total_count = await asyncio.to_thread(runtime.odoo.search_count, model, domain)
        rows = await asyncio.to_thread(
            runtime.odoo.search_read,
            model,
            domain,
            fields=standard_fields,
            limit=limit_value,
            offset=offset,
            order="id desc",
        )
        enriched_rows, warnings = await asyncio.to_thread(_enrich_task_rows, runtime.odoo, rows)
        task_fields = standard_fields + ["project_name", "stage_name", "assignees"]
        summary_extra: dict[str, Any] = {}
        if detail_level == "summary":
            sample_limit = min(total_count, TASK_SUMMARY_SAMPLE_LIMIT)
            aggregate_rows: list[dict[str, Any]]
            if sample_limit > 0:
                aggregate_rows = await asyncio.to_thread(
                    runtime.odoo.search_read,
                    model,
                    domain,
                    fields=runtime.odoo.existing_fields(model, ["id", "name", "stage_id", "user_ids", "active"]),
                    limit=sample_limit,
                    offset=0,
                    order="id desc",
                )
            else:
                aggregate_rows = []
            aggregation_complete = total_count <= TASK_SUMMARY_SAMPLE_LIMIT
            task_summary, aggregate_warnings = await asyncio.to_thread(
                _build_task_operational_summary,
                runtime.odoo,
                aggregate_rows,
                aggregation_complete=aggregation_complete,
                aggregation_sample_size=sample_limit,
            )
            summary_extra.update(task_summary)
            warnings.extend(aggregate_warnings)
            if not aggregation_complete:
                warnings.append("summary_sampled")
        return build_controlled_list_envelope(
            source="odoo",
            rows=enriched_rows,
            total_count=total_count,
            offset=offset,
            limit=limit_value,
            detail_level=detail_level,
            summary_fields=["id", "name", "project_id", "project_name", "stage_id", "stage_name", "assignees", "active"],
            standard_fields=task_fields,
            include_fields=include_fields,
            truncate_text=truncate_text,
            warnings=sorted(set(warnings)),
            summary=summary_extra,
        )

    @mcp.tool(
        name="get_task_by_id",
        title="Get Task By ID",
        description=(
            "Read-only detail lookup over Odoo `project.task` by numeric id. Returns one task with resolved `assignees`, "
            "`project_name`, and `stage_name`, or `warnings=['not_found']` when missing. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_task_by_id(task_id: int):
        model = "project.task"
        fields = runtime.odoo.existing_fields(
            model,
            ["id", "name", "display_name", "project_id", "user_ids", "company_id", "active", "stage_id"],
        )
        rows = await asyncio.to_thread(runtime.odoo.read, model, [int(task_id)], fields)
        enriched_rows, warnings = await asyncio.to_thread(_enrich_task_rows, runtime.odoo, rows)
        item = enriched_rows[0] if enriched_rows else None
        if item is None:
            warnings = ["not_found"]
        return build_single_record_result(
            source="odoo",
            item=item,
            warnings=warnings,
            summary={"model": model, "requested_id": int(task_id)},
        )

    @mcp.tool(
        name="count_helpdesk_tickets",
        title="Count Helpdesk Tickets",
        description=(
            "Count matching Odoo `helpdesk.ticket` rows before fetching pages. Supports the same free-text filter as "
            "`search_helpdesk_tickets` and returns no rows in `items`; read `summary.matched_count`. Cost: low."
        ),
        annotations=read_only,
    )
    async def count_helpdesk_tickets(query: str | None = None):
        model = "helpdesk.ticket"
        field_map = runtime.odoo.fields_get(model)
        domain: list[Any] = []
        if query:
            usable_search_fields = [field for field in ["name", "display_name"] if field in field_map]
            if usable_search_fields:
                domain.extend(_string_query_domain(usable_search_fields, query.strip()))
        matched_count = await asyncio.to_thread(runtime.odoo.search_count, model, domain)
        return build_count_result(source="odoo", matched_count=matched_count)

    @mcp.tool(
        name="search_helpdesk_tickets",
        title="Search Helpdesk Tickets",
        description=(
            "Read-only search over Odoo `helpdesk.ticket` for support operations adjacent to attendance and Odoo administration. "
            "Default output uses `detail_level=summary`. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_helpdesk_tickets(
        query: str | None = None,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        return await _search_odoo_model(
            model="helpdesk.ticket",
            query=query,
            detail_level=detail_level,
            limit=limit,
            cursor=cursor,
            order="id desc",
            candidate_fields=[
                "id",
                "name",
                "display_name",
                "partner_id",
                "user_id",
                "team_id",
                "stage_id",
                "priority",
                "create_date",
            ],
            summary_fields=["id", "name", "team_id", "stage_id", "priority", "create_date"],
            search_fields=["name", "display_name"],
            include_fields=include_fields,
            truncate_text=truncate_text,
            active=None,
        )

    @mcp.tool(
        name="get_helpdesk_ticket_by_id",
        title="Get Helpdesk Ticket By ID",
        description=(
            "Read-only detail lookup over Odoo `helpdesk.ticket` by numeric id. Use after `search_helpdesk_tickets` when you "
            "already have a record identifier. Returns one item when found or `warnings=['not_found']` when missing. Cost: low."
        ),
        annotations=read_only,
    )
    async def get_helpdesk_ticket_by_id(ticket_id: int):
        model = "helpdesk.ticket"
        fields = runtime.odoo.existing_fields(
            model,
            [
                "id",
                "name",
                "display_name",
                "partner_id",
                "user_id",
                "team_id",
                "stage_id",
                "priority",
                "create_date",
            ],
        )
        rows = await asyncio.to_thread(runtime.odoo.read, model, [int(ticket_id)], fields)
        item = rows[0] if rows else None
        warnings = [] if item is not None else ["not_found"]
        return build_single_record_result(
            source="odoo",
            item=item,
            warnings=warnings,
            summary={"model": model, "requested_id": int(ticket_id)},
        )

    @mcp.tool(
        name="search_users",
        title="Search Users",
        description=(
            "Read-only search over Odoo `res.users` for identity and operator lookup. Paginate with `limit` plus `cursor` "
            "and read `summary.total_count` before requesting more pages. Default output uses `detail_level=summary`. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_users(
        query: str | None = None,
        active: bool = True,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        return await _search_odoo_model(
            model="res.users",
            query=query,
            detail_level=detail_level,
            limit=limit,
            cursor=cursor,
            order="id asc",
            candidate_fields=["id", "name", "login", "partner_id", "company_id", "active", "share"],
            summary_fields=["id", "name", "login", "active", "share"],
            search_fields=["name", "login"],
            include_fields=include_fields,
            truncate_text=truncate_text,
            active=active,
        )

    @mcp.tool(
        name="search_contacts",
        title="Search Contacts",
        description=(
            "Read-only search over Odoo `res.partner` for contact-level business context. Paginate with `limit` plus `cursor` "
            "and read `summary.total_count` before requesting more pages. Default output uses `detail_level=summary`. Cost: low."
        ),
        annotations=read_only,
    )
    async def search_contacts(
        query: str | None = None,
        active: bool = True,
        detail_level: DetailLevel = "summary",
        limit: int | None = None,
        cursor: str | None = None,
        include_fields: list[str] | None = None,
        truncate_text: int | None = None,
    ):
        return await _search_odoo_model(
            model="res.partner",
            query=query,
            detail_level=detail_level,
            limit=limit,
            cursor=cursor,
            order="id asc",
            candidate_fields=["id", "name", "email", "phone", "mobile", "company_type", "active"],
            summary_fields=["id", "name", "email", "phone", "active"],
            search_fields=["name", "email", "phone", "mobile"],
            include_fields=include_fields,
            truncate_text=truncate_text,
            active=active,
        )

    return mcp
