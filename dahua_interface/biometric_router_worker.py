#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

from biometric_common import Settings, bootstrap_directories, configure_file_logger, ensure_directory
from biometric_db import BiometricDatabase


STATE_FILE_NAME = "router_state.json"
BAD_LINE_LOG_NAME = "bad_spool_lines.log"


@dataclass(slots=True)
class WorkerState:
    file_path: str = ""
    offset: int = 0


settings = Settings.from_env()
bootstrap_directories(settings)
logger = configure_file_logger("biometric_router_worker", settings.worker_log_path)


def state_path() -> Path:
    return settings.state_dir / STATE_FILE_NAME


def bad_line_log_path() -> Path:
    return settings.state_dir / BAD_LINE_LOG_NAME


def load_state() -> WorkerState:
    path = state_path()
    if not path.exists():
        return WorkerState()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Worker state file is invalid JSON, restarting from beginning path=%s", path)
        return WorkerState()
    return WorkerState(
        file_path=payload.get("file_path") or "",
        offset=int(payload.get("offset") or 0),
    )


def save_state(state: WorkerState) -> None:
    ensure_directory(settings.state_dir)
    payload = {
        "file_path": state.file_path,
        "offset": state.offset,
    }
    state_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_bad_line(file_path: Path, line: str, error_message: str) -> None:
    ensure_directory(settings.state_dir)
    with bad_line_log_path().open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "file_path": str(file_path),
                    "line": line.rstrip("\n"),
                    "error_message": error_message,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def spool_files() -> list[Path]:
    return sorted(settings.spool_dir.rglob("*.jsonl"))


def file_is_before(current: Path, state: WorkerState) -> bool:
    if not state.file_path:
        return False
    return str(current) < state.file_path


def process_file(db: BiometricDatabase, file_path: Path, state: WorkerState) -> bool:
    start_offset = state.offset if str(file_path) == state.file_path else 0
    with file_path.open("r", encoding="utf-8") as handle:
        handle.seek(start_offset)
        while True:
            line_offset = handle.tell()
            line = handle.readline()
            if not line:
                state.file_path = str(file_path)
                state.offset = handle.tell()
                save_state(state)
                return True

            stripped = line.strip()
            if not stripped:
                state.file_path = str(file_path)
                state.offset = handle.tell()
                save_state(state)
                continue

            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                append_bad_line(file_path, line, f"json_decode_error: {exc}")
                logger.error("Skipping invalid JSON line file=%s offset=%s error=%s", file_path, line_offset, exc)
                state.file_path = str(file_path)
                state.offset = handle.tell()
                save_state(state)
                continue

            try:
                db.process_spooled_event(payload)
            except psycopg.Error as exc:
                logger.exception(
                    "Database error while processing file=%s offset=%s ingest_id=%s error=%s",
                    file_path,
                    line_offset,
                    payload.get("ingest_id"),
                    exc,
                )
                return False
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Permanent processing failure file=%s offset=%s ingest_id=%s error=%s",
                    file_path,
                    line_offset,
                    payload.get("ingest_id"),
                    exc,
                )
                try:
                    db.record_processing_error(
                        stage="worker_process",
                        ingest_id=payload.get("ingest_id"),
                        error_message=str(exc),
                        payload=payload,
                        retryable=False,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Could not persist processing_error ingest_id=%s", payload.get("ingest_id"))
                state.file_path = str(file_path)
                state.offset = handle.tell()
                save_state(state)
                continue

            state.file_path = str(file_path)
            state.offset = handle.tell()
            save_state(state)


def work_loop() -> int:
    db: BiometricDatabase | None = None
    state = load_state()

    while True:
        try:
            if db is None:
                db = BiometricDatabase(settings)
                db.ensure_schema()
                logger.info("Connected to PostgreSQL and ensured schema")

            files = spool_files()
            if files:
                for file_path in files:
                    if file_is_before(file_path, state):
                        continue
                    if not process_file(db, file_path, state):
                        raise psycopg.OperationalError("worker_processing_failed")

            db.refresh_device_statuses()
            time.sleep(settings.worker_poll_seconds)
        except psycopg.Error as exc:
            logger.exception("Database connectivity problem: %s", exc)
            if db is not None:
                try:
                    db.close()
                except Exception:  # noqa: BLE001
                    logger.exception("Error while closing database connection")
            db = None
            time.sleep(max(settings.worker_poll_seconds, 5))
        except KeyboardInterrupt:
            logger.info("Worker interrupted")
            if db is not None:
                db.close()
            return 130
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected worker failure: %s", exc)
            if db is not None:
                try:
                    db.close()
                except Exception:  # noqa: BLE001
                    logger.exception("Error while closing database connection")
            db = None
            time.sleep(max(settings.worker_poll_seconds, 5))


if __name__ == "__main__":
    raise SystemExit(work_loop())
