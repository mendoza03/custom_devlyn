import json
from pathlib import Path
from typing import Any

import pymysql


class MySQLFallbackService:
    def __init__(self, connection_values_file: str):
        self.connection_values_file = connection_values_file

    def _read_connection(self) -> dict[str, Any]:
        path = Path(self.connection_values_file)
        if not path.exists():
            raise FileNotFoundError(f"Missing MySQL connection file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def write_event(self, payload: dict[str, Any]) -> None:
        cfg = self._read_connection()
        conn = pymysql.connect(
            host=cfg["db_host"],
            user=cfg["db_user"],
            password=cfg["db_password"],
            database=cfg["db_name"],
            connect_timeout=5,
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS biometric_events (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        event_type VARCHAR(64),
                        login_name VARCHAR(255),
                        result_status VARCHAR(64),
                        liveness_score DOUBLE NULL,
                        rekognition_session_id VARCHAR(255) NULL,
                        s3_video_url TEXT NULL,
                        payload_json JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cur.execute(
                    """
                    INSERT INTO biometric_events (
                        event_type, login_name, result_status, liveness_score,
                        rekognition_session_id, s3_video_url, payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload.get("event_type"),
                        payload.get("login"),
                        payload.get("result"),
                        payload.get("liveness_score"),
                        payload.get("rekognition_session_id"),
                        payload.get("s3_video_url"),
                        json.dumps(payload),
                    ),
                )
        finally:
            conn.close()
