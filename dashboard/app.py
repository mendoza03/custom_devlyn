from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

try:
    from .data_access import create_data_access
except ImportError:
    from data_access import create_data_access


APP_ROOT = Path(__file__).resolve().parent
STATIC_DIR = APP_ROOT / "static"

app = FastAPI(title="Dahua Dashboard Prototype", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@lru_cache(maxsize=1)
def _data_access():
    return create_data_access()


@app.get("/")
@app.get("/monitor.html")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/summary")
def api_summary() -> dict[str, Any]:
    return _data_access().get_summary()


@app.get("/api/{view_name}")
def api_view(
    view_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str = Query(default=""),
    event_kind: str = Query(default=""),
    reason: str = Query(default=""),
    status: str = Query(default=""),
    identity_resolution: str = Query(default=""),
    outcome: str = Query(default=""),
) -> dict[str, Any]:
    if view_name not in {"raw_requests", "normalized_events", "quarantine_events", "devices"}:
        raise HTTPException(status_code=404, detail="Unknown view")

    filters = {
        "event_kind": event_kind,
        "reason": reason,
        "status": status,
        "identity_resolution": identity_resolution,
        "outcome": outcome,
    }
    result = _data_access().get_page(
        view=view_name,
        page=page,
        page_size=page_size,
        search=search,
        filters={key: value for key, value in filters.items() if value},
    )
    return result.to_dict()


@app.get("/api/{view_name}/{record_id}")
def api_view_record(view_name: str, record_id: str) -> dict[str, Any]:
    if view_name not in {"raw_requests", "normalized_events", "quarantine_events", "devices"}:
        raise HTTPException(status_code=404, detail="Unknown view")
    record = _data_access().get_record(view=view_name, record_id=record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
