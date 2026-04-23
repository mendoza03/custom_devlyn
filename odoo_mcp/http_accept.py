from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

JSON_MEDIA_TYPE: Final[str] = "application/json"


@dataclass(frozen=True)
class ParsedAcceptItem:
    media_range: str
    q: float


def _parse_accept_header(value: str | None) -> list[ParsedAcceptItem]:
    if not value or not value.strip():
        return []

    items: list[ParsedAcceptItem] = []
    for chunk in value.split(","):
        part = chunk.strip()
        if not part:
            continue

        pieces = [piece.strip() for piece in part.split(";") if piece.strip()]
        media_range = pieces[0].lower()
        q = 1.0
        for piece in pieces[1:]:
            if "=" not in piece:
                continue
            name, raw_value = piece.split("=", 1)
            if name.strip().lower() != "q":
                continue
            try:
                q = float(raw_value.strip())
            except ValueError:
                q = 0.0
        items.append(ParsedAcceptItem(media_range=media_range, q=q))
    return items


def _match_specificity(media_range: str, target_media_type: str) -> int:
    target_type, target_subtype = target_media_type.lower().split("/", 1)
    if media_range == "*/*":
        return 0
    if "/" not in media_range:
        return -1

    media_type, media_subtype = media_range.split("/", 1)
    if media_type == "*" and media_subtype == "*":
        return 0
    if media_type == target_type and media_subtype == "*":
        return 1
    if media_type == target_type and media_subtype == target_subtype:
        return 2
    return -1


def accepts_media_type(value: str | None, target_media_type: str) -> bool:
    if not value or not value.strip():
        return True

    best_specificity = -1
    best_q = 0.0
    for item in _parse_accept_header(value):
        specificity = _match_specificity(item.media_range, target_media_type)
        if specificity < 0:
            continue
        if specificity > best_specificity:
            best_specificity = specificity
            best_q = item.q
            continue
        if specificity == best_specificity and item.q > best_q:
            best_q = item.q

    return best_specificity >= 0 and best_q > 0


def explicitly_accepts_media_type(value: str | None, target_media_type: str) -> bool:
    if not value or not value.strip():
        return False

    for item in _parse_accept_header(value):
        if item.media_range == target_media_type.lower() and item.q > 0:
            return True
    return False


def normalized_post_accept_header(value: str | None, *, target_media_type: str = JSON_MEDIA_TYPE) -> str | None:
    if not value or not value.strip():
        return target_media_type

    if not accepts_media_type(value, target_media_type):
        return None

    if explicitly_accepts_media_type(value, target_media_type):
        return None

    return f"{target_media_type}, {value}"


class McpPostAcceptCompatibilityMiddleware:
    """
    Normalize permissive POST Accept headers for MCP JSON-RPC requests.

    The upstream MCP python SDK currently requires a literal `application/json`
    token in POST `Accept` headers. Real clients often send `*/*`, `application/*`,
    or omit `Accept` entirely while still being able to consume JSON responses.
    This middleware preserves incompatible requests as-is so the SDK can continue
    returning 406 for truly unacceptable media ranges.
    """

    def __init__(self, app: ASGIApp, *, mcp_path: str):
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("method") == "POST" and scope.get("path") == self.mcp_path:
            headers = MutableHeaders(scope=scope)
            normalized = normalized_post_accept_header(headers.get("accept"))
            if normalized:
                headers["accept"] = normalized

        await self.app(scope, receive, send)
