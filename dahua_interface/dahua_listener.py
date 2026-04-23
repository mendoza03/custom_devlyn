from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


LOG_PATH = Path("/var/log/dahua_events.log")
LOGGER_NAME = "dahua_listener"


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = _configure_logger()
app = FastAPI(title="Dahua Debug Listener")


def _decode_body(body: bytes) -> str:
    if not body:
        return ""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("utf-8", errors="replace")


def _body_as_json_if_possible(body_text: str) -> Any:
    if not body_text:
        return None
    try:
        return json.loads(body_text)
    except json.JSONDecodeError:
        return body_text


async def _handle_request(request: Request, full_path: str = "") -> JSONResponse:
    body = await request.body()
    body_text = _decode_body(body)

    source_ip = request.client.host if request.client else "unknown"
    headers = dict(request.headers)
    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_ip": source_ip,
        "method": request.method,
        "path": "/" + full_path if full_path else request.url.path,
        "query": request.url.query,
        "headers": headers,
        "body": _body_as_json_if_possible(body_text),
        "body_raw": body_text,
    }

    logger.info("New request received")
    logger.info("Source IP: %s", source_ip)
    logger.info("Method: %s", request.method)
    logger.info("Path: %s", payload["path"])
    logger.info("Headers: %s", json.dumps(headers, ensure_ascii=False))
    logger.info("Body: %s", body_text or "<empty>")
    logger.info("Request dump: %s", json.dumps(payload, ensure_ascii=False, default=str))

    return JSONResponse(
        {
            "ok": True,
            "message": "received",
            "source_ip": source_ip,
            "method": request.method,
            "path": payload["path"],
        }
    )


@app.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def root_listener(request: Request) -> JSONResponse:
    return await _handle_request(request)


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def catch_all_listener(request: Request, full_path: str) -> JSONResponse:
    return await _handle_request(request, full_path)
