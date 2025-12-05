from __future__ import annotations

import hashlib
import os
import pickle
import time
from pathlib import Path
from typing import Generic, TypeVar

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
        value_with_expiry = self._store.get(key)
        if value_with_expiry is None:
            return None

        value, expiry_timestamp = value_with_expiry
        if _is_expired(expiry_timestamp):
            self.invalidate(key)
            return None

        return value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        self._store[key] = (value, _get_expiry_timestamp(ttl))

    def invalidate(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()


class FileCacheImpl(CacheABC[T]):
    """
    Файловый кэш с TTL.
    """

    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> T | None:
        cache_file = self._key_to_path(key)
        if not cache_file.exists():
            return None

        try:
            with cache_file.open("rb") as fh:
                payload: tuple[T, float | None] = pickle.load(fh)
        except (OSError, pickle.PickleError):
            self.invalidate(key)
            return None

        value, expiry_timestamp = payload
        if _is_expired(expiry_timestamp):
            self.invalidate(key)
            return None

        return value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        cache_file = self._key_to_path(key)
        tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
        payload: tuple[T, float | None] = (value, _get_expiry_timestamp(ttl))

        with tmp_file.open("wb") as fh:
            pickle.dump(payload, fh)

        os.replace(tmp_file, cache_file)

    def invalidate(self, key: str) -> None:
        cache_file = self._key_to_path(key)
        if cache_file.exists():
            cache_file.unlink(missing_ok=True)

    def clear(self) -> None:
        for cache_file in self._cache_dir.glob("*.cache"):
            cache_file.unlink(missing_ok=True)

    def _key_to_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        safe_name = f"{digest}.cache"
        return self._cache_dir / safe_name

