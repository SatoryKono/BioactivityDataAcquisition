"""Unit tests for MemoryLock."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest

from bioetl.domain.locking import FencingToken
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


@pytest.fixture
def fake_monotonic(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Patch memory lock monotonic clock for deterministic TTL tests."""
    current = {"value": 1000.0}

    def _now() -> float:
        return current["value"]

    def _advance(delta: float) -> None:
        current["value"] += delta

    monkeypatch.setattr(
        "bioetl.infrastructure.locking.memory_lock.time.monotonic",
        _now,
    )
    return _advance


@pytest.mark.unit
class TestMemoryLock:
    """Tests for MemoryLock."""

    @pytest.mark.asyncio
    async def test_acquire_success(self, memory_lock):
        """Test successful lock acquisition returns FencingToken."""
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=True,
            exclusive=True,
        )
        assert result is not None
        assert isinstance(result, FencingToken)
        assert result.sequence == 1
        assert result.key == "test_key"

    @pytest.mark.asyncio
    async def test_validate_fencing_token_success(self, memory_lock):
        """Test fencing token validation succeeds for current holder."""
        token = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )
        assert token is not None

        result = await memory_lock.validate_fencing_token("test_key", token)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_fencing_token_rejects_stale(self, memory_lock):
        """Test fencing token validation fails for stale tokens."""
        token = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )
        assert token is not None
        await memory_lock.release(key="test_key", owner_id="owner_1")

        new_token = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_2",
        )
        assert new_token is not None

        result = await memory_lock.validate_fencing_token("test_key", token)
        assert result is False

    @pytest.mark.asyncio
    async def test_acquire_no_wait_when_unlocked(self, memory_lock):
        """Test acquire with wait=False when lock is not held."""
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=False,
        )
        # When wait=False and lock is not held, acquire succeeds immediately
        assert result is not None
        assert isinstance(result, FencingToken)

    @pytest.mark.asyncio
    async def test_acquire_timeout(self, memory_lock, monkeypatch: pytest.MonkeyPatch):
        """Test acquire with timeout when lock is held."""
        # First acquire the lock
        await memory_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            wait=True,
        )

        real_sleep = asyncio.sleep

        async def _fast_sleep(_seconds: float) -> None:
            await real_sleep(0)

        monkeypatch.setattr(
            "bioetl.infrastructure.locking.memory_lock.asyncio.sleep",
            _fast_sleep,
        )

        # Try to acquire again with short timeout
        result = await memory_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=True,
            wait_timeout=0.0001,
        )
        assert result is None

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
    async def test_held_lock_is_not_force_released_after_ttl(
        self, fast_ttl_lock, fake_monotonic
    ):
        """Still-held process-local locks survive TTL sweeps.

        Force-dropping a held lock mid-write caused write_gold LockNotHeldError
        when heartbeats were delayed by long Silver stages.
        """
        token = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=0.3,
        )
        assert token is not None

        # Another owner cannot acquire while the lock is held.
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

        # Advance past TTL and trigger expiration scan.
        fake_monotonic(0.45)
        await fast_ttl_lock._release_expired_locks()

        # Owner still holds the lock; fencing validation renews the lease.
        assert await fast_ttl_lock.validate_fencing_token("test_key", token) is True
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

        # Explicit release is still required to free the key.
        assert await fast_ttl_lock.release("test_key", "owner_1") is True
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is not None

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_soft_expired_unlocked_entry_is_reaped(
        self, fast_ttl_lock, fake_monotonic
    ):
        """TTL sweep drops soft-expired entries that are no longer locked."""
        token = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=0.3,
        )
        assert token is not None
        # Manually unlock without deleting the map entry to simulate a stale row.
        owner, lock, expires_at, original_ttl, sequence = fast_ttl_lock._locks[
            "test_key"
        ]
        if lock.locked():
            lock.release()
        fast_ttl_lock._locks["test_key"] = (
            owner,
            lock,
            expires_at,
            original_ttl,
            sequence,
        )

        fake_monotonic(0.45)
        await fast_ttl_lock._release_expired_locks()
        assert "test_key" not in fast_ttl_lock._locks

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_memory_lock_t_t_l__extends_ttl__6750e69a(
        self, fast_ttl_lock, fake_monotonic
    ):
        """Test that heartbeat extends the lock TTL."""
        # Acquire lock with TTL
        await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
            ttl=1.0,  # 1s TTL (reduced from 2s; sufficient for heartbeat test)
        )

        # Advance time without real waiting.
        fake_monotonic(0.1)

        # Heartbeat to extend TTL (resets to 1s from now)
        result = await fast_ttl_lock.heartbeat(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is True

        # Advance again and force a TTL sweep. The heartbeat should keep the lock alive.
        fake_monotonic(0.15)
        await fast_ttl_lock._release_expired_locks()

        # Lock should still be held because heartbeat extended it
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

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
    async def test_lock_without_ttl_does_not_expire(
        self, fast_ttl_lock, fake_monotonic
    ):
        """Test that lock without TTL never expires automatically."""
        # Acquire lock without TTL
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_1",
        )
        assert result is not None

        # Advance time and run TTL sweep; TTL-less locks should remain held.
        fake_monotonic(0.3)
        await fast_ttl_lock._release_expired_locks()

        # Lock should still be held
        result = await fast_ttl_lock.acquire(
            key="test_key",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_multiple_locks_with_different_ttl(
        self, fast_ttl_lock, fake_monotonic
    ):
        """Test multiple locks with different TTL values stay held while locked."""
        # Acquire two locks with different TTLs (increased for CI stability)
        await fast_ttl_lock.acquire(
            key="short_ttl",
            owner_id="owner_1",
            ttl=0.3,  # 300ms (increased from 100ms for CI stability)
        )
        await fast_ttl_lock.acquire(
            key="long_ttl",
            owner_id="owner_1",
            ttl=1.0,  # 1s (increased from 500ms for CI stability)
        )

        # Advance past the short TTL; held locks are not force-released.
        fake_monotonic(0.45)
        await fast_ttl_lock._release_expired_locks()

        # Short TTL lock remains held by owner_1 until explicit release.
        result = await fast_ttl_lock.acquire(
            key="short_ttl",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

        # Long TTL lock should still be held
        result = await fast_ttl_lock.acquire(
            key="long_ttl",
            owner_id="owner_2",
            wait=False,
        )
        assert result is None

        # After explicit release, the short key can be re-acquired.
        assert await fast_ttl_lock.release("short_ttl", "owner_1") is True
        result = await fast_ttl_lock.acquire(
            key="short_ttl",
            owner_id="owner_2",
            wait=False,
        )
        assert result is not None

        await fast_ttl_lock.aclose()

    @pytest.mark.asyncio
    async def test_sequence_monotonically_increases(self, memory_lock):
        """Test that fencing token sequence increases across acquires."""
        # Acquire and release three times on the same key
        sequences = []
        for i in range(3):
            token = await memory_lock.acquire(
                key="test_key",
                owner_id=f"owner_{i}",
            )
            assert token is not None
            sequences.append(token.sequence)
            await memory_lock.release(key="test_key", owner_id=f"owner_{i}")

        # Sequences must be strictly increasing
        assert sequences == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_sequence_increases_across_different_keys(self, memory_lock):
        """Test that sequence counter is global, not per-key."""
        t1 = await memory_lock.acquire(key="key_a", owner_id="owner_1")
        t2 = await memory_lock.acquire(key="key_b", owner_id="owner_1")

        assert t1 is not None
        assert t2 is not None
        assert t2.sequence > t1.sequence
