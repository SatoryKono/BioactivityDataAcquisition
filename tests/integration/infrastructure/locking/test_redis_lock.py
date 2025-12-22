"""Integration tests for RedisDistributedLock using fakeredis.

This ensures proper behavior of:
- Lock acquisition and release
- TTL expiration
- Exclusive vs Shared locking semantics
- Re-entrancy behavior (strictly non-reentrant)
- Heartbeat loop
"""

import asyncio
from uuid import uuid4

import pytest

from bioetl.domain.types import RunID
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

# Use fakeredis for integration tests as per plan
# This works without a real Redis instance but validates logic fully.
# If a real Redis was needed, we would conditionally use the `redis_client` fixture.


@pytest.fixture
async def redis_lock(fake_redis):
    """Provide a RedisDistributedLock instance using fake_redis."""
    lock = RedisDistributedLock(
        redis_client=fake_redis, default_ttl=2, heartbeat_interval=1
    )
    # Ensure scripts are loaded
    await lock._ensure_scripts()
    return lock


@pytest.mark.asyncio
class TestRedisDistributedLock:
    """Integration tests for RedisDistributedLock."""

    async def test_acquire_and_release_success(
        self, redis_lock: RedisDistributedLock, run_id: RunID
    ) -> None:
        """Test basic acquire and release cycle."""
        key = "test_resource"

        # Acquire
        acquired = await redis_lock.acquire(key, run_id)
        assert acquired is True
        assert await redis_lock.is_locked(key) is True
        assert await redis_lock.get_owner(key) == str(run_id)

        # Release
        released = await redis_lock.release(key, run_id)
        assert released is True
        assert await redis_lock.is_locked(key) is False
        assert await redis_lock.get_owner(key) is None

    async def test_acquire_conflict(self, redis_lock: RedisDistributedLock) -> None:
        """Test that a second acquirer fails."""
        key = "conflict_resource"
        owner1 = RunID(uuid4())
        owner2 = RunID(uuid4())

        # Owner 1 acquires
        await redis_lock.acquire(key, owner1)

        # Owner 2 tries to acquire same key
        acquired = await redis_lock.acquire(key, owner2)
        assert acquired is False

        # Verify owner is still Owner 1
        assert await redis_lock.get_owner(key) == str(owner1)

    async def test_non_reentrant(
        self, redis_lock: RedisDistributedLock, run_id: RunID
    ) -> None:
        """Verify the lock is non-reentrant even for the same owner."""
        key = "reentrant_check"

        await redis_lock.acquire(key, run_id)

        # Try to acquire again
        acquired = await redis_lock.acquire(key, run_id)
        assert acquired is False

    async def test_release_wrong_owner(self, redis_lock: RedisDistributedLock) -> None:
        """Test that releasing with wrong owner fails and keeps lock."""
        key = "security_check"
        owner1 = RunID(uuid4())
        owner2 = RunID(uuid4())

        await redis_lock.acquire(key, owner1)

        # Owner 2 tries to release
        released = await redis_lock.release(key, owner2)
        assert released is False
        assert await redis_lock.is_locked(key) is True

    async def test_ttl_expiration(
        self, redis_lock: RedisDistributedLock, run_id: RunID
    ) -> None:
        """Test that lock expires after TTL."""
        key = "ttl_check"
        # Use short TTL
        ttl = 1
        await redis_lock.acquire(key, run_id, ttl=ttl)
        assert await redis_lock.is_locked(key) is True

        # Wait for expiration
        await asyncio.sleep(ttl + 0.1)

        assert await redis_lock.is_locked(key) is False

    async def test_exclusive_vs_shared_locking(
        self, redis_lock: RedisDistributedLock
    ) -> None:
        """Test mutual exclusion between 'shared' (regular) and exclusive modes."""
        key = "mode_check"
        owner1 = RunID(uuid4())
        owner2 = RunID(uuid4())

        # 1. Regular holds, Exclusive tries
        await redis_lock.acquire(key, owner1, exclusive=False)
        assert await redis_lock.acquire(key, owner2, exclusive=True) is False
        await redis_lock.release(key, owner1, exclusive=False)

        # 2. Exclusive holds, Regular tries
        await redis_lock.acquire(key, owner1, exclusive=True)
        assert await redis_lock.acquire(key, owner2, exclusive=False) is False
        await redis_lock.release(key, owner1, exclusive=True)

        # 3. Regular holds, Regular tries (also exclusive cardinality)
        await redis_lock.acquire(key, owner1, exclusive=False)
        assert await redis_lock.acquire(key, owner2, exclusive=False) is False
        await redis_lock.release(key, owner1, exclusive=False)

    async def test_heartbeat_extends_ttl(
        self, redis_lock: RedisDistributedLock, run_id: RunID
    ) -> None:
        """Test that heartbeat extends the lock."""
        key = "heartbeat_check"
        ttl = 1
        await redis_lock.acquire(key, run_id, ttl=ttl)

        # Sleep 0.6s (remaining 0.4s)
        await asyncio.sleep(0.6)

        # Send heartbeat -> resets to default_ttl (2s in fixture)
        success = await redis_lock.heartbeat(key, run_id)
        assert success is True

        # Sleep another 0.6s (total 1.2s since start, would have expired if not for heartbeat)
        await asyncio.sleep(0.6)

        assert await redis_lock.is_locked(key) is True

    async def test_wait_acquire(self, redis_lock: RedisDistributedLock) -> None:
        """Test waiting for a lock."""
        key = "wait_check"
        owner1 = RunID(uuid4())
        owner2 = RunID(uuid4())

        await redis_lock.acquire(key, owner1, ttl=1)

        # Owner 2 waits. Owner 1 expires after 1s. Wait timeout is 2s.
        # It should succeed after ~1s
        acquired = await redis_lock.acquire(key, owner2, wait=True, wait_timeout=2)
        assert acquired is True
        assert await redis_lock.get_owner(key) == str(owner2)
