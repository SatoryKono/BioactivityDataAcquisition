from typing import Any, Generic, TypeVar

from bioetl.infrastructure.clients.base.contracts import CacheABC

T = TypeVar("T")


class MemoryCacheImpl(CacheABC[T]):
    """
    Простой кэш в памяти.
    """

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def get(self, key: str) -> T | None:
        return self._store.get(key)

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        # TTL ignored in simple memory cache for now
        self._store[key] = value

    def invalidate(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()


class FileCacheImpl(CacheABC[T]):
    """
    Файловый кэш (заглушка).
    """

    def __init__(self, cache_dir: str) -> None:
        self.cache_dir = cache_dir

    def get(self, key: str) -> T | None:
        return None

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        pass

    def invalidate(self, key: str) -> None:
        pass

    def clear(self) -> None:
        pass

