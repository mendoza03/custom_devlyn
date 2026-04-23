from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _CacheItem(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._values: dict[str, _CacheItem[T]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._values.pop(key, None)
                return None
            return item.value

    def set(self, key: str, value: T) -> T:
        with self._lock:
            self._values[key] = _CacheItem(value=value, expires_at=time.monotonic() + self._ttl_seconds)
        return value

    def clear(self) -> None:
        with self._lock:
            self._values.clear()
