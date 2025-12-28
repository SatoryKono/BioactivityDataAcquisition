"""Unit tests for MemoryLock."""

from __future__ import annotations

import asyncio

import pytest

from bioetl.infrastructure.locking.memory_lock import MemoryLock


@pytest.fixture
def memory_lock():
    """Create a MemoryLock instance."""
    return MemoryLock()


@pytest.fixture
def fast_ttl_lock():
    """Create a MemoryLock with fast TTL checking for tests.

    Uses aggressive interval (20ms) for faster test execution.
    """
    return MemoryLock(ttl_check_interval=0.02)


@pytest.mark.unit
class TestMemoryLock:
    """Tests for MemoryLock."""

    @pytest.mark.asyncio
    async def test_acquire_success(self, memory_lock):
        """Test successful lock acquisition."""
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=True,
            exclusive=True,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_no_wait_when_unlocked(self, memory_lock):
        """Test acquire with wait=False when lock is not held."""
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=False,
        )
        # When wait=False and lock is not held, acquire succeeds immediately
        assert result is True

    @pytest.mark.asyncio
    async def test_acquire_timeout(self, memory_lock):
        """Test acquire with timeout when lock is held."""
        # First acquire the lock
        await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=True,
        )

        # Try to acquire again with short timeout
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=True,
            wait_timeout=0.01,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_release_success(self, memory_lock):
        """Test successful lock release."""
        await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )

        result = await memory_lock.release(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_release_unlocked(self, memory_lock):
        """Test release when lock is not held."""
        result = await memory_lock.release(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, memory_lock):
        """Test heartbeat succeeds when lock is held by owner."""
        # Acquire lock first
        await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )
        result = await memory_lock.heartbeat(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_heartbeat_fails_when_not_owned(self, memory_lock):
        """Test heartbeat fails when lock is not held or owned by other."""
        # Case 1: No lock
        result = await memory_lock.heartbeat(
            key="nonexistent_key",
            owner_id="owner_1",
        )
        assert result is False

        # Case 2: Owned by other
        await memory_lock.acquire(
            key="test_key",
            owner_id="owner_2",
        )
        result = await memory_lock.heartbeat(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_aclose_releases_locks(self, memory_lock):
        """Test aclose releases all locks."""
        await memory_lock.acquire(key="key1", owner_id="owner_1")
        await memory_lock.acquire(key="key2", owner_id="owner_2")

        await memory_lock.aclose()

        # Locks should be cleared
        assert len(memory_lock._locks) == 0


@pytest.mark.unit
class TestMemoryLockTTL:
    """Tests for MemoryLock TTL expiration functionality."""

    @pytest.mark.asyncio
    async def test_lock_expires_after_ttl(self, fast_ttl_lock):
        """Test that lock is automatically released after TTL expires."""
        # Acquire lock with short TTL (optimized for fast test execution)
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=0.1,  # 100ms TTL (was 1s)
        )
        assert result is True

        # Another owner cannot acquire immediately
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is False

        # Wait for TTL to expire (TTL + check interval buffer)
        await asyncio.sleep(0.15)

        # Now another owner should be able to acquire
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is True

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_heartbeat_extends_ttl(self, fast_ttl_lock):
        """Test that heartbeat extends the lock TTL."""
        # Acquire lock with short TTL (optimized for fast test execution)
        await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=0.1,  # 100ms TTL (was 1s)
        )

        # Wait half the TTL
        await asyncio.sleep(0.05)

        # Heartbeat to extend TTL
        result = await fast_ttl_lock.heartbeat(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

        # Wait another 0.07s (original TTL would have expired)
        await asyncio.sleep(0.07)

        # Lock should still be held because heartbeat extended it
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is False

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_ttl_checker_starts_only_when_needed(self):
        """Test that TTL checker task starts only when acquiring with TTL."""
        lock = MemoryLock(ttl_check_interval=0.1)

        # No TTL checker before any acquire
        assert lock._ttl_checker_task is None

        # Acquire without TTL - no checker started
        await lock.acquire(key="key1", owner_id="owner_1")
        assert lock._ttl_checker_task is None

        # Acquire with TTL - checker should start
        await lock.acquire(key="key2", owner_id="owner_1", ttl=10)
        assert lock._ttl_checker_task is not None
        assert not lock._ttl_checker_task.done()

        await lock.aclose()

    @pytest.mark.asyncio
    async def test_aclose_stops_ttl_checker(self, fast_ttl_lock):
        """Test that aclose stops the TTL checker task."""
        # Acquire with TTL to start the checker
        await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=10,
        )

        # Checker should be running
        assert fast_ttl_lock._ttl_checker_task is not None

        await fast_ttl_lock.aclose()

        # Checker should be stopped and cleared
        assert fast_ttl_lock._ttl_checker_task is None
        assert fast_ttl_lock._closed is True

    @pytest.mark.asyncio
    async def test_lock_without_ttl_does_not_expire(self, fast_ttl_lock):
        """Test that lock without TTL never expires automatically."""
        # Acquire lock without TTL
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

        # Wait some time (would have expired if TTL was set)
        await asyncio.sleep(0.3)

        # Lock should still be held
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is False

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_multiple_locks_with_different_ttl(self, fast_ttl_lock):
        """Test multiple locks with different TTL values."""
        # Acquire two locks with different TTLs (optimized for fast test execution)
        await fast_ttl_lock.acquire(
            key="short_ttl",
            owner_id="owner_1",
            ttl=0.1,  # 100ms (was 1s)
        )
        await fast_ttl_lock.acquire(
            key="long_ttl",
            owner_id="owner_1",
            ttl=0.5,  # 500ms (was 5s)
        )

        # Wait for short TTL to expire
        await asyncio.sleep(0.15)

        # Short TTL lock should be available
        result = await fast_ttl_lock.acquire(
            key="short_ttl",
            owner_id="owner_2",
            wait=False,
        )
        assert result is True

        # Long TTL lock should still be held
        result = await fast_ttl_lock.acquire(
            key="long_ttl",
            owner_id="owner_2",
            wait=False,
        )
        assert result is False

        await fast_ttl_lock.aclose()
