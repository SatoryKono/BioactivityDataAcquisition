"""In-memory cache implementation with TTL support."""

from __future__ import annotations

import time
from typing import TypeVar

from bioetl.domain.clients.base.contracts import CacheABC

T = TypeVar("T")


def _get_expiry_timestamp(ttl: int | None) -> float | None:
    return time.time() + ttl if ttl is not None else None


def _is_expired(expiry_timestamp: float | None) -> bool:
    return expiry_timestamp is not None and expiry_timestamp <= time.time()


class MemoryCacheImpl(CacheABC[T]):
    """
    Простой кэш в памяти.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[T, float | None]] = {}

    def get(self, key: str) -> T | None:
        """Return cached value if present and not expired."""
        value_with_expiry = self._store.get(key)
        if value_with_expiry is None:
            return None

        value, expiry_timestamp = value_with_expiry
        if _is_expired(expiry_timestamp):
            self.invalidate(key)
            return None

        return value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store value with optional TTL."""
        self._store[key] = (value, _get_expiry_timestamp(ttl))

    def invalidate(self, key: str) -> None:
        """Remove entry from cache if present."""
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """Clear entire in-memory cache."""
        self._store.clear()
