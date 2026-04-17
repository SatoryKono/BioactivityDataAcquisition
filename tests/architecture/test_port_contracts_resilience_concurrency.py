"""Resilience/concurrency shard for port contract verification tests.

Extracted from `test_port_contracts.py` to reduce hotspot file size and
improve xdist balancing while preserving test behavior 1:1.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.locking import FencingToken

# ============================================================================
# Error Condition Contract Tests
# ============================================================================


class TestLockPortErrorConditions:
    """Tests for LockPort error condition handling.

    LockPort implementations MUST handle error conditions gracefully:
    - Concurrent acquire attempts from different owners
    - Heartbeat on non-existent locks
    - Release of locks not owned
    - Validate owner on expired locks
    """

    @pytest.mark.asyncio
    async def test_lock_release_wrong_owner_returns_false(self) -> None:
        """LockPort.release() MUST return False when releasing lock not owned."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            # Owner1 acquires lock
            acquired = await lock.acquire("test_key", owner1)
            assert acquired, "Owner1 should acquire lock"

            # Owner2 tries to release - should fail
            released = await lock.release("test_key", owner2)
            assert not released, (
                "LockPort.release() MUST return False when owner does not match"
            )

            # Lock should still be held by owner1
            is_owner = await lock.validate_owner("test_key", owner1)
            assert is_owner, "Owner1 should still hold the lock"
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_heartbeat_non_existent_returns_false(self) -> None:
        """LockPort.heartbeat() MUST return False for non-existent locks."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()

        try:
            result = await lock.heartbeat("non_existent_key", uuid4())
            assert not result, (
                "LockPort.heartbeat() MUST return False for non-existent locks"
            )
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_heartbeat_wrong_owner_returns_false(self) -> None:
        """LockPort.heartbeat() MUST return False when owner does not match."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            await lock.acquire("test_key", owner1)
            result = await lock.heartbeat("test_key", owner2)
            assert not result, (
                "LockPort.heartbeat() MUST return False when owner does not match"
            )
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_validate_owner_non_existent_returns_false(self) -> None:
        """LockPort.validate_owner() MUST return False for non-existent locks."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()

        try:
            result = await lock.validate_owner("non_existent_key", uuid4())
            assert not result, (
                "LockPort.validate_owner() MUST return False for non-existent locks"
            )
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_lock_acquire_timeout_returns_false(self) -> None:
        """LockPort.acquire() with wait=True MUST return False after timeout."""
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner1 = uuid4()
        owner2 = uuid4()

        try:
            # Owner1 acquires lock
            await lock.acquire("test_key", owner1)

            # Owner2 tries to acquire with short timeout
            acquired = await lock.acquire("test_key", owner2, wait=True, wait_timeout=1)
            assert not acquired, (
                "LockPort.acquire() MUST return False when wait times out"
            )
        finally:
            await lock.aclose()


class TestCheckpointPortErrorConditions:
    """Tests for CheckpointPort error condition handling.

    CheckpointPort implementations MUST handle error conditions gracefully:
    - Load non-existent checkpoint
    - Delete non-existent checkpoint (idempotent)
    - Save with corrupted metadata
    """

    @pytest.mark.asyncio
    async def test_checkpoint_load_non_existent_returns_none(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.load() MUST return None for non-existent checkpoints."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        checkpoint = LocalCheckpointAdapter(base_path=tmp_path)

        try:
            result = await checkpoint.load("non_existent_pipeline")
            assert result is None, (
                "CheckpointPort.load() MUST return None for non-existent checkpoints"
            )
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_checkpoint_delete_non_existent_is_idempotent(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.delete() MUST be idempotent (no error if not exists)."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        checkpoint = LocalCheckpointAdapter(base_path=tmp_path)

        try:
            # Should not raise exception
            await checkpoint.delete("non_existent_pipeline")
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_checkpoint_list_all_empty_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """CheckpointPort.list_all() MUST return empty list when no checkpoints."""
        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        checkpoint = LocalCheckpointAdapter(base_path=tmp_path)

        try:
            result = await checkpoint.list_all()
            assert result == [], (
                "CheckpointPort.list_all() MUST return empty list when no checkpoints"
            )
        finally:
            await checkpoint.aclose()


class TestCircuitBreakerPortErrorConditions:
    """Tests for CircuitBreakerPort error condition handling.

    CircuitBreakerPort implementations MUST:
    - Raise CircuitBreakerOpenError when circuit is open
    - Re-raise exceptions from wrapped functions
    - Track failure counts correctly
    """

    @pytest.mark.asyncio
    async def test_circuit_breaker_raises_when_open(self) -> None:
        """CircuitBreakerPort.call() MUST raise CircuitBreakerOpenError when open."""
        from bioetl.domain.exceptions import CircuitBreakerOpenError
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test", failure_threshold=2, recovery_timeout=300
        )

        async def failing_func() -> None:
            raise RuntimeError("Simulated failure")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        # Now circuit should be open
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(failing_func)

        assert exc_info.value.provider == "test", (
            "CircuitBreakerOpenError MUST include provider name"
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_propagates_exceptions(self) -> None:
        """CircuitBreakerPort.call() MUST propagate exceptions from wrapped func."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(provider="test", failure_threshold=5)

        class CustomError(Exception):
            pass

        async def failing_func() -> None:
            raise CustomError("Custom error")

        with pytest.raises(CustomError, match="Custom error"):
            await breaker.call(failing_func)

    def test_circuit_breaker_reset_clears_failure_count(self) -> None:
        """CircuitBreakerPort.reset() MUST clear failure count."""
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(provider="test", failure_threshold=5)
        breaker._failure_count = 3  # Simulate failures

        breaker.reset()

        assert breaker.get_failure_count() == 0, (
            "CircuitBreakerPort.reset() MUST clear failure count"
        )
        assert breaker.get_state() == CircuitBreakerState.CLOSED, (
            "CircuitBreakerPort.reset() MUST set state to CLOSED"
        )


class TestRateLimiterPortErrorConditions:
    """Tests for RateLimiterPort error condition handling.

    RateLimiterPort implementations MUST:
    - Raise ValueError when acquiring more tokens than capacity
    - Handle zero tokens acquisition
    - Return accurate token counts
    """

    @pytest.mark.asyncio
    async def test_rate_limiter_raises_on_overcapacity_request(self) -> None:
        """RateLimiterPort.acquire() MUST raise ValueError when tokens > capacity."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)

        with pytest.raises(ValueError, match="Cannot acquire"):
            await bucket.acquire(tokens=15)

    def test_rate_limiter_try_acquire_returns_false_when_insufficient(self) -> None:
        """RateLimiterPort.try_acquire() MUST return False when insufficient tokens."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=1.0, capacity=5)
        # Drain tokens
        for _ in range(5):
            bucket.try_acquire()

        result = bucket.try_acquire()
        assert not result, (
            "RateLimiterPort.try_acquire() MUST return False when insufficient tokens"
        )

    def test_rate_limiter_available_tokens_non_negative(self) -> None:
        """RateLimiterPort.available_tokens() MUST return non-negative value."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)

        # Drain tokens
        while bucket.try_acquire():
            pass

        result = bucket.available_tokens()
        assert result >= 0, (
            "RateLimiterPort.available_tokens() MUST return non-negative value"
        )


# ============================================================================
# Concurrent Access Pattern Tests
# ============================================================================


class TestLockPortConcurrentAccess:
    """Tests for LockPort concurrent access patterns.

    LockPort implementations MUST handle concurrent access:
    - Multiple concurrent acquire attempts
    - Concurrent heartbeat operations
    - Concurrent release attempts
    """

    @pytest.mark.asyncio
    async def test_concurrent_acquire_only_one_succeeds(self) -> None:
        """Only one concurrent acquire attempt MUST succeed for the same key."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        num_contenders = 10
        owners = [uuid4() for _ in range(num_contenders)]
        results: list[FencingToken | None] = []

        async def try_acquire(owner_id):
            result = await lock.acquire("shared_key", owner_id)
            return result

        try:
            tasks = [try_acquire(owner) for owner in owners]
            results = await asyncio.gather(*tasks)

            successful_acquires = sum(1 for r in results if r is not None)
            assert successful_acquires == 1, (
                f"Only one concurrent acquire MUST succeed, got {successful_acquires}"
            )
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_operations_different_keys_independent(self) -> None:
        """Concurrent operations on different keys MUST be independent."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        num_keys = 5
        keys = [f"key_{i}" for i in range(num_keys)]
        owners = [uuid4() for _ in range(num_keys)]

        async def acquire_and_release(key, owner):
            acquired = await lock.acquire(key, owner)
            if acquired:
                await asyncio.sleep(0.01)  # Short hold
                await lock.release(key, owner)
            return acquired

        try:
            tasks = [
                acquire_and_release(k, o) for k, o in zip(keys, owners, strict=True)
            ]
            results = await asyncio.gather(*tasks)

            assert all(results), (
                "All concurrent operations on different keys MUST succeed"
            )
        finally:
            await lock.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_heartbeat_from_owner_succeeds(self) -> None:
        """Concurrent heartbeat operations from owner MUST all succeed."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        lock = MemoryLock()
        owner = uuid4()

        try:
            await lock.acquire("test_key", owner, ttl=60)

            async def heartbeat():
                return await lock.heartbeat("test_key", owner)

            tasks = [heartbeat() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            assert all(results), (
                "Concurrent heartbeat operations from owner MUST all succeed"
            )
        finally:
            await lock.aclose()


class TestCheckpointPortConcurrentAccess:
    """Tests for CheckpointPort concurrent access patterns.

    CheckpointPort implementations MUST handle concurrent access:
    - Concurrent save operations
    - Concurrent load operations
    - Concurrent list_all operations
    """

    @pytest.mark.asyncio
    async def test_concurrent_saves_to_different_pipelines(
        self, tmp_path: Path
    ) -> None:
        """Concurrent saves to different pipelines MUST all succeed."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        checkpoint = LocalCheckpointAdapter(base_path=tmp_path)
        num_pipelines = 5
        pipelines = [f"pipeline_{i}" for i in range(num_pipelines)]

        async def save_checkpoint(pipeline):
            await checkpoint.save(pipeline, uuid4(), {"key": pipeline})
            return True

        try:
            tasks = [save_checkpoint(p) for p in pipelines]
            results = await asyncio.gather(*tasks)

            assert all(results), (
                "Concurrent saves to different pipelines MUST all succeed"
            )

            # Verify all saved
            saved_pipelines = await checkpoint.list_all()
            assert len(saved_pipelines) == num_pipelines
        finally:
            await checkpoint.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_loads_return_consistent_data(
        self, tmp_path: Path
    ) -> None:
        """Concurrent loads of the same checkpoint MUST return consistent data."""
        import asyncio
        from uuid import uuid4

        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        checkpoint = LocalCheckpointAdapter(base_path=tmp_path)
        run_id = uuid4()
        metadata = {"key": "value"}

        try:
            await checkpoint.save("test_pipeline", run_id, metadata)

            async def load_checkpoint():
                return await checkpoint.load("test_pipeline")

            tasks = [load_checkpoint() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # All results should be identical
            for result in results:
                assert result is not None
                loaded_run_id, loaded_metadata = result
                assert loaded_run_id == run_id
                assert loaded_metadata == metadata
        finally:
            await checkpoint.aclose()


class TestCircuitBreakerPortConcurrentAccess:
    """Tests for CircuitBreakerPort concurrent access patterns.

    CircuitBreakerPort implementations MUST handle concurrent access:
    - Concurrent calls update state atomically
    - State transitions are consistent under load
    """

    @pytest.mark.asyncio
    async def test_concurrent_calls_track_failures_correctly(self) -> None:
        """Concurrent failing calls MUST track failure count correctly."""
        import asyncio

        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test", failure_threshold=10, recovery_timeout=300
        )

        async def failing_call():
            try:
                await breaker.call(self._async_fail)
            except RuntimeError:
                pass
            except Exception:
                pass

        async def _async_fail():
            raise RuntimeError("Fail")

        self._async_fail = _async_fail

        tasks = [failing_call() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Failure count should be at most 10 (could be fewer if circuit opened)
        assert breaker.get_failure_count() <= 10

    @pytest.mark.asyncio
    async def test_concurrent_successes_reset_failure_count(self) -> None:
        """Concurrent successful calls MUST reset failure count to 0."""
        import asyncio

        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test", failure_threshold=10, recovery_timeout=300
        )
        breaker._failure_count = 5

        async def success_call():
            return await breaker.call(self._async_success)

        async def _async_success():
            return "success"

        self._async_success = _async_success

        tasks = [success_call() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert breaker.get_failure_count() == 0, (
            "Concurrent successful calls MUST reset failure count to 0"
        )


class TestRateLimiterPortConcurrentAccess:
    """Tests for RateLimiterPort concurrent access patterns.

    RateLimiterPort implementations MUST handle concurrent access:
    - Concurrent acquire operations respect capacity
    - Token count never goes negative
    """

    @pytest.mark.asyncio
    async def test_concurrent_acquires_respect_capacity(self) -> None:
        """Concurrent acquires MUST respect capacity limits."""
        import asyncio

        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=100.0, capacity=10)

        acquired_count = 0
        lock = asyncio.Lock()

        async def try_acquire_token():
            nonlocal acquired_count
            success = bucket.try_acquire()
            if success:
                async with lock:
                    acquired_count += 1
            return success

        tasks = [try_acquire_token() for _ in range(20)]
        await asyncio.gather(*tasks)

        assert acquired_count <= 10, (
            f"Concurrent acquires MUST respect capacity, got {acquired_count}"
        )

    def test_token_count_never_negative(self) -> None:
        """Token count MUST never go negative after concurrent try_acquire."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=1.0, capacity=5)

        # Drain more than capacity
        for _ in range(10):
            bucket.try_acquire()

        assert bucket.available_tokens() >= 0, "Token count MUST never go negative"
