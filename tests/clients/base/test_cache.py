"""
Tests for cache implementations.
"""
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl, FileCacheImpl


def test_memory_cache():
    """Test memory cache operations."""
    cache = MemoryCacheImpl[int]()
    cache.set("k", 1)
    assert cache.get("k") == 1
    cache.invalidate("k")
    assert cache.get("k") is None

    cache.set("k2", 2)
    cache.clear()
    assert cache.get("k2") is None


def test_file_cache():
    """Test file cache operations (stub)."""
    # Stub test
    cache = FileCacheImpl("/tmp")
    cache.set("k", 1)
    assert cache.get("k") is None
    cache.invalidate("k")
    cache.clear()
