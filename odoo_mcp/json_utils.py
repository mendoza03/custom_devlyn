from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import orjson


def _default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def dumps(value: Any, *, indent: bool = False) -> bytes:
    option = 0
    if indent:
        option |= orjson.OPT_INDENT_2
    return orjson.dumps(value, default=_default, option=option)


def dumps_text(value: Any, *, indent: bool = False) -> str:
    return dumps(value, indent=indent).decode("utf-8")


def loads(value: str | bytes) -> Any:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return orjson.loads(value)


def json_response_payload(value: Any) -> bytes:
    return dumps(value, indent=False)


def to_plain_json(value: Any) -> Any:
    return json.loads(dumps(value))
