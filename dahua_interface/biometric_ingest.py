from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from biometric_common import (
    Settings,
    append_jsonl_with_fsync,
    bootstrap_directories,
    classify_event,
    configure_file_logger,
    decode_body,
    determine_payload_hash,
    extract_device_id_hint,
    extract_device_model,
    extract_listener_port,
    extract_source_ip,
    generate_ingest_id,
    host_identifier,
    is_loopback_ip,
    json_dumps,
    parse_json_if_possible,
    spool_file_for_timestamp,
    utc_now,
    utc_now_iso,
)


settings = Settings.from_env()
bootstrap_directories(settings)

request_logger = configure_file_logger("biometric_ingest.request", settings.request_log_path)
app_logger = configure_file_logger("biometric_ingest.app", settings.ingest_log_path)

app = FastAPI(title="Biometric Event Ingest")


def _is_internal_probe(request: Request, source_ip: str) -> bool:
    if request.url.path == "/__health":
        return True
    return is_loopback_ip(source_ip)


def _request_payload_for_logs(
    *,
    ingest_id: str,
    received_at_utc: str,
    source_ip: str,
    source_port: int | None,
    listener_port: int,
    method: str,
    path: str,
    query: str,
    headers: dict[str, Any],
    body: Any,
    body_raw: str,
    event_kind_detected: str,
    device_id_hint: str | None,
    device_model_hint: str | None,
    payload_hash: str,
) -> dict[str, Any]:
    return {
        "timestamp_utc": received_at_utc,
        "received_at_utc": received_at_utc,
        "ingest_id": ingest_id,
        "source_ip": source_ip,
        "source_port": source_port,
        "listener_port": listener_port,
        "method": method,
        "path": path,
        "query": query,
        "headers": headers,
        "body": body,
        "body_raw": body_raw,
        "event_kind_detected": event_kind_detected,
        "device_id_hint": device_id_hint,
        "device_model_hint": device_model_hint,
        "payload_hash": payload_hash,
        "ingest_host": host_identifier(),
    }


async def _handle_request(request: Request, full_path: str = "") -> JSONResponse:
    raw_body = await request.body()
    if len(raw_body) > settings.max_body_bytes:
        raise HTTPException(status_code=413, detail="payload_too_large")

    body_raw = decode_body(raw_body)
    body = parse_json_if_possible(body_raw)
    headers = dict(request.headers)

    source_ip = extract_source_ip(headers, request.client.host if request.client else None)
    source_port = request.client.port if request.client else None
    listener_port = extract_listener_port(headers, settings.public_listener_port)
    method = request.method.upper()
    path = "/" + full_path if full_path else request.url.path
    query = request.url.query

    if method != "POST" and not _is_internal_probe(request, source_ip):
        raise HTTPException(status_code=405, detail="method_not_allowed")

    ingest_id = generate_ingest_id()
    received_at_utc = utc_now_iso()
    event_kind_detected = classify_event(path, body)
    device_id_hint = extract_device_id_hint(body, path)
    device_model_hint = extract_device_model(body)
    payload_hash = determine_payload_hash(
        source_ip=source_ip,
        listener_port=listener_port,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body_raw=body_raw,
    )

    spool_event = {
        "ingest_id": ingest_id,
        "received_at_utc": received_at_utc,
        "source_ip": source_ip,
        "source_port": source_port,
        "listener_port": listener_port,
        "method": method,
        "path": path,
        "query": query,
        "headers": headers,
        "body": body,
        "body_raw": body_raw,
        "payload_hash": payload_hash,
        "event_kind_detected": event_kind_detected,
        "device_id_hint": device_id_hint,
        "device_model_hint": device_model_hint,
    }

    spool_path = spool_file_for_timestamp(settings.spool_dir, utc_now())
    try:
        append_jsonl_with_fsync(spool_path, spool_event)
    except Exception as exc:  # noqa: BLE001
        app_logger.exception("Failed to append request to spool path=%s error=%s", spool_path, exc)
        raise HTTPException(status_code=503, detail="ingest_spool_unavailable") from exc

    log_payload = _request_payload_for_logs(
        ingest_id=ingest_id,
        received_at_utc=received_at_utc,
        source_ip=source_ip,
        source_port=source_port,
        listener_port=listener_port,
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
        body_raw=body_raw,
        event_kind_detected=event_kind_detected,
        device_id_hint=device_id_hint,
        device_model_hint=device_model_hint,
        payload_hash=payload_hash,
    )

    request_logger.info("New request received")
    request_logger.info("Source IP: %s", source_ip)
    request_logger.info("Method: %s", method)
    request_logger.info("Path: %s", path)
    request_logger.info("Headers: %s", json.dumps(headers, ensure_ascii=False))
    request_logger.info("Body: %s", body_raw or "<empty>")
    request_logger.info("Request dump: %s", json_dumps(log_payload))

    app_logger.info(
        "ingested ingest_id=%s event_kind=%s source_ip=%s listener_port=%s path=%s spool=%s",
        ingest_id,
        event_kind_detected,
        source_ip,
        listener_port,
        path,
        spool_path,
    )

    return JSONResponse(
        {
            "ok": True,
            "message": "received",
            "ingest_id": ingest_id,
            "event_kind_detected": event_kind_detected,
            "source_ip": source_ip,
            "method": method,
            "path": path,
        }
    )


@app.get("/__health")
async def healthcheck() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "biometric-ingest",
            "time_utc": utc_now_iso(),
        }
    )


@app.api_route("/", methods=["POST", "GET", "HEAD"])
async def root_listener(request: Request) -> JSONResponse:
    return await _handle_request(request)


@app.api_route("/{full_path:path}", methods=["POST", "GET", "HEAD"])
async def catch_all_listener(request: Request, full_path: str) -> JSONResponse:
    return await _handle_request(request, full_path)
