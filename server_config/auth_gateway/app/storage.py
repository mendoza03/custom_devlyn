import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any


_logger = logging.getLogger(__name__)

DB_PATH = Path(os.getenv("AUTH_GATEWAY_DB_PATH", "/opt/auth-gateway/data/gateway.db"))
FALLBACK_DB_PATH = Path(os.getenv("AUTH_GATEWAY_DB_FALLBACK_PATH", "./.auth_gateway_data/gateway.db"))


class FlowStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            fallback = FALLBACK_DB_PATH
            fallback.parent.mkdir(parents=True, exist_ok=True)
            _logger.warning(
                "No write permission for DB path '%s'. Falling back to '%s'.",
                self.db_path,
                fallback,
            )
            self.db_path = fallback
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS flow_state (
                    flow_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    username TEXT,
                    cognito_access_token TEXT,
                    cognito_id_token TEXT,
                    cognito_refresh_token TEXT,
                    cognito_sub TEXT,
                    liveness_session_id TEXT,
                    liveness_attempts INTEGER DEFAULT 0,
                    liveness_score REAL,
                    liveness_passed INTEGER DEFAULT 0,
                    s3_video_url TEXT,
                    next_logout_url TEXT,
                    status TEXT,
                    context_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def create_flow(self, flow_id: str, kind: str, values: dict[str, Any]):
        data = {
            "flow_id": flow_id,
            "kind": kind,
            "username": values.get("username"),
            "cognito_access_token": values.get("cognito_access_token"),
            "cognito_id_token": values.get("cognito_id_token"),
            "cognito_refresh_token": values.get("cognito_refresh_token"),
            "cognito_sub": values.get("cognito_sub"),
            "liveness_session_id": values.get("liveness_session_id"),
            "liveness_attempts": values.get("liveness_attempts", 0),
            "liveness_score": values.get("liveness_score"),
            "liveness_passed": 1 if values.get("liveness_passed") else 0,
            "s3_video_url": values.get("s3_video_url"),
            "next_logout_url": values.get("next_logout_url"),
            "status": values.get("status", "created"),
            "context_json": json.dumps(values.get("context", {})),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO flow_state (
                    flow_id, kind, username, cognito_access_token, cognito_id_token,
                    cognito_refresh_token, cognito_sub, liveness_session_id,
                    liveness_attempts, liveness_score, liveness_passed, s3_video_url,
                    next_logout_url, status, context_json
                ) VALUES (
                    :flow_id, :kind, :username, :cognito_access_token, :cognito_id_token,
                    :cognito_refresh_token, :cognito_sub, :liveness_session_id,
                    :liveness_attempts, :liveness_score, :liveness_passed, :s3_video_url,
                    :next_logout_url, :status, :context_json
                )
                """,
                data,
            )

    def get_flow(self, flow_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM flow_state WHERE flow_id = ?", (flow_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["liveness_passed"] = bool(result["liveness_passed"])
        result["context"] = json.loads(result.pop("context_json") or "{}")
        return result

    def update_flow(self, flow_id: str, values: dict[str, Any]):
        if not values:
            return
        sets = []
        params: dict[str, Any] = {"flow_id": flow_id}
        for key, value in values.items():
            if key == "context":
                key = "context_json"
                value = json.dumps(value)
            if key == "liveness_passed":
                value = 1 if value else 0
            sets.append(f"{key} = :{key}")
            params[key] = value
        sets.append("updated_at = CURRENT_TIMESTAMP")
        with self._connect() as conn:
            conn.execute(
                f"UPDATE flow_state SET {', '.join(sets)} WHERE flow_id = :flow_id",
                params,
            )
