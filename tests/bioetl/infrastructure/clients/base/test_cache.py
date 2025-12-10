"""
Tests for cache implementations.
"""

import time

from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl


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


def test_memory_cache_ttl_expiration():
    """Test TTL expiration in memory cache."""
    cache = MemoryCacheImpl[int]()
    cache.set("k", 10, ttl=1)
    time.sleep(1.2)
    assert cache.get("k") is None
