from __future__ import annotations

import base64

from odoo_mcp.json_utils import dumps, loads


def encode_offset_cursor(offset: int) -> str | None:
    if offset <= 0:
        return None
    raw = dumps({"offset": offset})
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_offset_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
    payload = loads(raw)
    offset = int(payload.get("offset", 0))
    return max(offset, 0)
