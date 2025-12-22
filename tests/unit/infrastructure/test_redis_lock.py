"""Unit tests for RedisDistributedLock."""

from __future__ import annotations

from uuid import uuid4

import pytest

from bioetl.domain.types import RunID


@pytest.mark.parametrize("redis_client_fixture", ["fake_redis"])
@pytest.mark.unit
class TestRedisDistributedLock:
    """Tests for Redis-based distributed locking."""

    @pytest.mark.asyncio
    async def test_acquire_lock(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Should successfully acquire an available lock."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        acquired = await lock.acquire("test_key", run_id)
        assert acquired is True

        # Verify lock exists
        assert await lock.is_locked("test_key") is True

        # Verify owner
        owner = await lock.get_owner("test_key")
        assert owner == str(run_id)

    @pytest.mark.asyncio
    async def test_acquire_fails_if_locked(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Should fail to acquire if already locked by another owner."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        # First owner acquires
        await lock.acquire("test_key", run_id)

        # Second owner tries to acquire
        acquired = await lock.acquire("test_key", other_owner)
        assert acquired is False

    @pytest.mark.asyncio
    async def test_release_lock(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Should successfully release owned lock."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        await lock.acquire("test_key", run_id)
        released = await lock.release("test_key", run_id)

        assert released is True
        assert await lock.is_locked("test_key") is False

    @pytest.mark.asyncio
    async def test_release_fails_if_not_owner(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Should fail to release lock owned by another."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        await lock.acquire("test_key", run_id)
        released = await lock.release("test_key", other_owner)

        assert released is False
        assert await lock.is_locked("test_key") is True  # Still locked

    @pytest.mark.asyncio
    async def test_heartbeat_extends_ttl(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat should extend lock TTL."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        await lock.acquire("test_key", run_id, ttl=10)

        # Heartbeat should succeed and extend TTL
        success = await lock.heartbeat("test_key", run_id)
        assert success is True

    @pytest.mark.asyncio
    async def test_heartbeat_fails_if_not_owner(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat should fail if not owner."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        await lock.acquire("test_key", run_id)

        success = await lock.heartbeat("test_key", other_owner)
        assert success is False

    @pytest.mark.asyncio
    async def test_heartbeat_fails_if_lock_expired(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat should fail if lock has expired."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        # Try heartbeat without acquiring
        success = await lock.heartbeat("nonexistent_key", run_id)
        assert success is False

    @pytest.mark.asyncio
    async def test_exclusive_lock(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Exclusive lock should block regular locks."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        # Acquire exclusive lock
        acquired = await lock.acquire("test_key", run_id, exclusive=True)
        assert acquired is True

        # Regular lock should fail
        regular_acquired = await lock.acquire("test_key", other_owner)
        assert regular_acquired is False

        # Release exclusive lock
        await lock.release("test_key", run_id, exclusive=True)

        # Regular lock should now succeed
        regular_acquired = await lock.acquire("test_key", other_owner)
        assert regular_acquired is True

    @pytest.mark.asyncio
    async def test_exclusive_fails_if_regular_exists(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Exclusive lock should fail if regular lock exists."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        # Acquire regular lock first
        await lock.acquire("test_key", run_id)

        # Exclusive lock should fail
        exclusive_acquired = await lock.acquire("test_key", other_owner, exclusive=True)
        assert exclusive_acquired is False

    @pytest.mark.asyncio
    async def test_key_prefix(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Lock keys should use configured prefix."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(
            redis_client=redis_client,
            prefix="bioetl_lock",
        )

        await lock.acquire("test_key", run_id)

        # Key should be prefixed
        exists = await redis_client.exists("bioetl_lock:test_key")
        assert exists > 0

    @pytest.mark.asyncio
    async def test_get_owner_nonexistent_key(
        self, redis_client_fixture, request
    ) -> None:
        """Get owner should return None for nonexistent key."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        owner = await lock.get_owner("nonexistent_key")
        assert owner is None

    @pytest.mark.asyncio
    async def test_is_locked_nonexistent_key(
        self, redis_client_fixture, request
    ) -> None:
        """Is locked should return False for nonexistent key."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        is_locked = await lock.is_locked("nonexistent_key")
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_aclose(self, redis_client_fixture, request, run_id: RunID) -> None:
        """aclose should close the Redis connection."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        # aclose should complete without error
        await lock.aclose()

    @pytest.mark.asyncio
    async def test_heartbeat_exclusive(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat should work with exclusive locks."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        await lock.acquire("test_key", run_id, exclusive=True)
        success = await lock.heartbeat("test_key", run_id, exclusive=True)
        assert success is True

    @pytest.mark.asyncio
    async def test_is_locked_exclusive(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Is locked should work with exclusive locks."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        await lock.acquire("test_key", run_id, exclusive=True)
        is_locked = await lock.is_locked("test_key", exclusive=True)
        assert is_locked is True

    @pytest.mark.asyncio
    async def test_get_owner_exclusive(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Get owner should work with exclusive locks."""
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)

        await lock.acquire("test_key", run_id, exclusive=True)
        owner = await lock.get_owner("test_key", exclusive=True)
        assert owner == str(run_id)

    @pytest.mark.asyncio
    async def test_acquire_with_wait_succeeds_when_released(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Wait should succeed when lock is released by other owner."""
        import asyncio

        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        # First owner acquires
        await lock.acquire("test_key", run_id, ttl=5)

        # Start task to release after delay
        async def release_after_delay():
            await asyncio.sleep(0.3)
            await lock.release("test_key", run_id)

        release_task = asyncio.create_task(release_after_delay())

        # Second owner waits for lock (should succeed after release)
        acquired = await lock.acquire(
            "test_key", other_owner, wait=True, wait_timeout=5
        )
        assert acquired is True

        await release_task

    @pytest.mark.asyncio
    async def test_acquire_with_wait_times_out(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Wait should raise LockAcquisitionError when timeout expires."""
        from bioetl.domain.exceptions import LockAcquisitionError
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(redis_client=redis_client)
        other_owner = RunID(uuid4())

        # First owner acquires lock and holds it
        await lock.acquire("test_key", run_id, ttl=120)

        # Second owner waits but times out
        with pytest.raises(LockAcquisitionError):
            await lock.acquire("test_key", other_owner, wait=True, wait_timeout=1)

    @pytest.mark.asyncio
    async def test_heartbeat_loop_raises_on_lock_lost(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat loop should raise LockLostError when lock is lost."""
        import asyncio

        from bioetl.domain.exceptions import LockLostError
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(
            redis_client=redis_client,
            heartbeat_interval=0.1,  # Fast heartbeat for test
        )

        await lock.acquire("test_key", run_id, ttl=5)

        # Event to track if on_lost is called
        on_lost = asyncio.Event()

        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(
            lock.heartbeat_loop("test_key", run_id, on_lost=on_lost)
        )

        # Delete the lock key to simulate lock loss
        await asyncio.sleep(0.05)
        redis_key = lock._make_key("test_key")
        await redis_client.delete(redis_key)

        # Heartbeat loop should raise LockLostError
        with pytest.raises(LockLostError):
            await asyncio.wait_for(heartbeat_task, timeout=1.0)

        # on_lost event should be set
        assert on_lost.is_set()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_raises_on_max_duration(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """Heartbeat loop should raise LockLostError when max duration exceeded."""
        import asyncio

        from bioetl.domain.exceptions import LockLostError
        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        redis_client = request.getfixturevalue(redis_client_fixture)
        lock = RedisDistributedLock(
            redis_client=redis_client,
            heartbeat_interval=0.1,
            max_duration=0.1,  # Very short for test
        )

        await lock.acquire("test_key", run_id, ttl=5)

        on_lost = asyncio.Event()

        with pytest.raises(LockLostError):
            await asyncio.wait_for(
                lock.heartbeat_loop("test_key", run_id, on_lost=on_lost),
                timeout=1.0,
            )

        assert on_lost.is_set()

    @pytest.mark.asyncio
    async def test_aclose_with_close_method(
        self, redis_client_fixture, request, run_id: RunID
    ) -> None:
        """aclose should call close() if aclose() not available."""
        from unittest.mock import AsyncMock, MagicMock

        from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

        # Create a mock client with only close() method
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        # Explicitly remove aclose
        del mock_client.aclose

        lock = RedisDistributedLock(redis_client=mock_client)
        await lock.aclose()

        mock_client.close.assert_called_once()
