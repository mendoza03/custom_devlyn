import logging
import time
from typing import Any

from .mysql_fallback import MySQLFallbackService
from .odoo_service import OdooService

_logger = logging.getLogger(__name__)


class EventService:
    def __init__(
        self,
        odoo_service: OdooService,
        mysql_fallback_enabled: bool,
        mysql_fallback_service: MySQLFallbackService | None,
    ):
        self.odoo_service = odoo_service
        self.mysql_fallback_enabled = mysql_fallback_enabled
        self.mysql_fallback_service = mysql_fallback_service

    def emit(self, payload: dict[str, Any]) -> None:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                self.odoo_service.post_event(payload)
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                _logger.warning("Odoo event post failed attempt=%s error=%s", attempt, exc)
                time.sleep(0.5)

        if self.mysql_fallback_enabled and self.mysql_fallback_service:
            try:
                self.mysql_fallback_service.write_event(payload)
                _logger.warning("Event written to MySQL fallback")
                return
            except Exception as exc:  # noqa: BLE001
                _logger.error("MySQL fallback failed: %s", exc)

        if last_error:
            raise last_error
