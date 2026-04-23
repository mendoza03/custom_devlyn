from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_DAHUA_LOG_PATH = Path("/var/log/dahua_events.log")
DEVICE_PATH_RE = re.compile(r"^/d/([A-Za-z0-9][A-Za-z0-9_.-]{0,127})(?:/.*)?$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)


def parse_json_if_possible(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def decode_body(body: bytes) -> str:
    if not body:
        return ""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("utf-8", errors="replace")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_ingest_id() -> str:
    return str(uuid4())


def determine_payload_hash(
    *,
    source_ip: str,
    listener_port: int,
    method: str,
    path: str,
    query: str,
    headers: dict[str, Any],
    body_raw: str,
) -> str:
    canonical = {
        "source_ip": source_ip,
        "listener_port": listener_port,
        "method": method.upper(),
        "path": path,
        "query": query,
        "headers": headers,
        "body_raw": body_raw,
    }
    return sha256_text(json_dumps(canonical))


def normalize_ip(ip_text: str | None) -> str | None:
    if not ip_text:
        return None
    raw = ip_text.strip()
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return raw


def extract_source_ip(headers: dict[str, Any], fallback: str | None) -> str:
    forwarded = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        normalized = normalize_ip(first)
        if normalized:
            return normalized
    real_ip = headers.get("x-real-ip") or headers.get("X-Real-IP")
    normalized = normalize_ip(real_ip)
    if normalized:
        return normalized
    return normalize_ip(fallback) or "unknown"


def extract_listener_port(headers: dict[str, Any], default_port: int) -> int:
    raw = headers.get("x-listener-port") or headers.get("X-Listener-Port")
    if raw is None:
        return default_port
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default_port


def classify_event(path: str, body: Any) -> str:
    if path == "/cgi-bin/api/autoRegist/connect":
        return "heartbeat_connect"
    if isinstance(body, dict):
        code = body.get("Code")
        if code == "AccessControl":
            return "access_control"
        if code == "DoorStatus":
            return "door_status"
    return "unknown"


def extract_device_id_from_path(path: str) -> str | None:
    if not path:
        return None
    match = DEVICE_PATH_RE.match(path)
    if not match:
        return None
    return match.group(1)


def extract_device_id_hint(body: Any, path: str = "") -> str | None:
    if isinstance(body, dict):
        device_id = body.get("DeviceID")
        if isinstance(device_id, str) and device_id.strip():
            return device_id.strip()
    return extract_device_id_from_path(path)


def extract_device_model(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    return body.get("DevClass")


def select_event_epoch(body: Any) -> int | None:
    if not isinstance(body, dict):
        return None

    if body.get("Code") in {"AccessControl", "DoorStatus"}:
        data = body.get("Data")
        if isinstance(data, dict):
            for key in ("RealUTC", "UTC", "CreateTime"):
                value = data.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str) and value.isdigit():
                    return int(value)

    for key in ("RealUTC", "UTC", "CreateTime"):
        value = body.get(key)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def epoch_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def normalize_direction(raw: Any) -> str:
    if raw == "Entry":
        return "entry"
    if raw == "Exit":
        return "exit"
    return "unknown"


def normalize_granted(raw: Any) -> bool | None:
    if raw == 1 or raw == "1":
        return True
    if raw == 0 or raw == "0":
        return False
    return None


def parse_int(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def compute_dedup_key(
    *,
    event_kind: str,
    device_id: str | None,
    block_id: int | None,
    event_occurred_at: datetime,
    user_id_on_device: str | None,
    reader_id: str | None,
    door_name: str | None,
    method_code: int | None,
    granted: bool | None,
) -> str:
    resolved_device_id = device_id or "unknown-device"
    if block_id is not None:
        return f"{resolved_device_id}|{event_kind}|block|{block_id}"
    granted_raw = "true" if granted is True else "false" if granted is False else "null"
    components = [
        resolved_device_id,
        event_kind,
        event_occurred_at.astimezone(timezone.utc).isoformat(),
        user_id_on_device or "",
        reader_id or "",
        door_name or "",
        str(method_code) if method_code is not None else "",
        granted_raw,
    ]
    return sha256_text("|".join(components))


def spool_file_for_timestamp(base_dir: Path, value: datetime) -> Path:
    base = ensure_directory(base_dir / value.strftime("%Y") / value.strftime("%m") / value.strftime("%d"))
    return base / f"events-{value.strftime('%Y%m%d')}.jsonl"


def append_jsonl_with_fsync(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    line = json_dumps(payload) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def configure_file_logger(name: str, log_path: Path) -> logging.Logger:
    ensure_directory(log_path.parent)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def is_loopback_ip(ip_text: str | None) -> bool:
    if not ip_text:
        return False
    try:
        return ipaddress.ip_address(ip_text).is_loopback
    except ValueError:
        return False


def host_identifier() -> str:
    return socket.gethostname()


@dataclass(frozen=True)
class Settings:
    public_listener_port: int
    internal_listener_port: int
    spool_dir: Path
    state_dir: Path
    archive_dir: Path
    request_log_path: Path
    ingest_log_path: Path
    worker_log_path: Path
    database_url: str
    heartbeat_window_seconds: int
    stale_after_seconds: int
    offline_after_seconds: int
    worker_poll_seconds: float
    max_body_bytes: int
    heartbeat_expected_interval_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            public_listener_port=int(os.getenv("BIOMETRIC_PUBLIC_PORT", "60005")),
            internal_listener_port=int(os.getenv("BIOMETRIC_INTERNAL_PORT", "60006")),
            spool_dir=Path(os.getenv("BIOMETRIC_SPOOL_DIR", "/var/lib/biometric-ingest/spool")),
            state_dir=Path(os.getenv("BIOMETRIC_STATE_DIR", "/var/lib/biometric-ingest/state")),
            archive_dir=Path(os.getenv("BIOMETRIC_ARCHIVE_DIR", "/var/lib/biometric-ingest/archive")),
            request_log_path=Path(os.getenv("BIOMETRIC_REQUEST_LOG", str(DEFAULT_DAHUA_LOG_PATH))),
            ingest_log_path=Path(os.getenv("BIOMETRIC_INGEST_LOG", "/var/log/biometric-ingest/ingest.log")),
            worker_log_path=Path(os.getenv("BIOMETRIC_WORKER_LOG", "/var/log/biometric-ingest/worker.log")),
            database_url=os.getenv(
                "BIOMETRIC_DATABASE_URL",
                "postgresql://biometric_app:change_me@127.0.0.1:5432/biometric_ingest",
            ),
            heartbeat_window_seconds=int(os.getenv("BIOMETRIC_HEARTBEAT_WINDOW_SECONDS", "600")),
            stale_after_seconds=int(os.getenv("BIOMETRIC_STALE_AFTER_SECONDS", "120")),
            offline_after_seconds=int(os.getenv("BIOMETRIC_OFFLINE_AFTER_SECONDS", "300")),
            worker_poll_seconds=float(os.getenv("BIOMETRIC_WORKER_POLL_SECONDS", "2")),
            max_body_bytes=int(os.getenv("BIOMETRIC_MAX_BODY_BYTES", "131072")),
            heartbeat_expected_interval_seconds=int(
                os.getenv("BIOMETRIC_HEARTBEAT_EXPECTED_INTERVAL_SECONDS", "30")
            ),
        )


def bootstrap_directories(settings: Settings) -> None:
    ensure_directory(settings.spool_dir)
    ensure_directory(settings.state_dir)
    ensure_directory(settings.archive_dir)
    ensure_directory(settings.request_log_path.parent)
    ensure_directory(settings.ingest_log_path.parent)
    ensure_directory(settings.worker_log_path.parent)
