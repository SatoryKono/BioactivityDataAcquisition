"""Unit tests for RedisDistributedLock."""

from __future__ import annotations

from uuid import uuid4

import pytest

from bioetl.domain.types import RunID


@pytest.mark.unit
class TestRedisDistributedLock:
    """Tests for Redis-based distributed locking."""

    @pytest.mark.asyncio
    async def test_acquire_lock(self, fake_redis: object, run_id: RunID) -> None:
        """Should successfully acquire an available lock."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]

        acquired = await lock.acquire("test_key", run_id)
        assert acquired is True

        # Verify lock exists
        assert await lock.is_locked("test_key") is True

        # Verify owner
        owner = await lock.get_owner("test_key")
        assert owner == str(run_id)

    @pytest.mark.asyncio
    async def test_acquire_fails_if_locked(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Should fail to acquire if already locked by another owner."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]
        other_owner = RunID(uuid4())

        # First owner acquires
        await lock.acquire("test_key", run_id)

        # Second owner tries to acquire
        acquired = await lock.acquire("test_key", other_owner)
        assert acquired is False

    @pytest.mark.asyncio
    async def test_release_lock(self, fake_redis: object, run_id: RunID) -> None:
        """Should successfully release owned lock."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]

        await lock.acquire("test_key", run_id)
        released = await lock.release("test_key", run_id)

        assert released is True
        assert await lock.is_locked("test_key") is False

    @pytest.mark.asyncio
    async def test_release_fails_if_not_owner(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Should fail to release lock owned by another."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]
        other_owner = RunID(uuid4())

        await lock.acquire("test_key", run_id)
        released = await lock.release("test_key", other_owner)

        assert released is False
        assert await lock.is_locked("test_key") is True  # Still locked

    @pytest.mark.asyncio
    async def test_heartbeat_extends_ttl(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Heartbeat should extend lock TTL."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]

        await lock.acquire("test_key", run_id, ttl=10)

        # Heartbeat should succeed and extend TTL
        success = await lock.heartbeat("test_key", run_id)
        assert success is True

    @pytest.mark.asyncio
    async def test_heartbeat_fails_if_not_owner(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Heartbeat should fail if not owner."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]
        other_owner = RunID(uuid4())

        await lock.acquire("test_key", run_id)

        success = await lock.heartbeat("test_key", other_owner)
        assert success is False

    @pytest.mark.asyncio
    async def test_heartbeat_fails_if_lock_expired(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Heartbeat should fail if lock has expired."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]

        # Try heartbeat without acquiring
        success = await lock.heartbeat("nonexistent_key", run_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_exclusive_lock(self, fake_redis: object, run_id: RunID) -> None:
        """Exclusive lock should block regular locks."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]
        other_owner = RunID(uuid4())

        # Acquire exclusive lock
        acquired = await lock.acquire_exclusive("test_key", run_id)
        assert acquired is True

        # Regular lock should fail (exclusive key is locked)
        regular_acquired = await lock.acquire("test_key:exclusive", other_owner)
        assert regular_acquired is False

    @pytest.mark.asyncio
    async def test_exclusive_fails_if_regular_exists(
        self, fake_redis: object, run_id: RunID
    ) -> None:
        """Exclusive lock should fail if regular lock exists."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(redis_client=fake_redis)  # type: ignore[arg-type]
        other_owner = RunID(uuid4())

        # Acquire regular lock first
        await lock.acquire("test_key", run_id)

        # Exclusive lock should fail
        exclusive_acquired = await lock.acquire_exclusive("test_key", other_owner)
        assert exclusive_acquired is False

    @pytest.mark.asyncio
    async def test_key_prefix(self, fake_redis: object, run_id: RunID) -> None:
        """Lock keys should use configured prefix."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        lock = RedisDistributedLock(
            redis_client=fake_redis,  # type: ignore[arg-type]
            prefix="bioetl_lock",
        )

        await lock.acquire("test_key", run_id)

        # Key should be prefixed
        exists = await fake_redis.exists("bioetl_lock:test_key")  # type: ignore[union-attr]
        assert exists > 0