"""Unit tests for MemoryLock."""

import asyncio

import pytest

from bioetl.infrastructure.locking.memory_lock import MemoryLock


@pytest.fixture
def memory_lock():
    """Create a MemoryLock instance."""
    return MemoryLock()


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
    async def test_heartbeat_always_succeeds(self, memory_lock):
        """Test that heartbeat always returns True."""
        result = await memory_lock.heartbeat(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_heartbeat_without_lock(self, memory_lock):
        """Test heartbeat without holding lock still succeeds."""
        result = await memory_lock.heartbeat(
            key="nonexistent_key",
            owner_id="owner_1",
        )
        assert result is True
