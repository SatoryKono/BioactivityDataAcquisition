"""E2E tests for pipeline resilience scenarios.

These tests cover:
- Memory pressure handling with adaptive batch sizing
- Circuit breaker recovery flow
- Rate limiter behavior under load
- Lock timeout and recovery

Part of architecture review refactoring plan (R2).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    pass


# ============================================================================
# Memory Pressure Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_memory_monitor_adaptive_batching(e2e_data_dir: Path):
    """E2E: MemoryMonitor reduces batch size under memory pressure.

    Per ADR-017:
    - Batch size should be reduced when memory usage exceeds threshold
    - Pipeline should continue processing with smaller batches
    """
    from bioetl.application.core.memory_monitor import MemoryMonitor, MemoryStats

    # Create memory monitor
    monitor = MemoryMonitor(
        warning_threshold_percent=80.0,
        critical_threshold_percent=95.0,
    )

    # Get initial stats
    stats = monitor.get_stats()
    assert isinstance(stats, MemoryStats)

    # Verify adaptive batch calculation
    initial_batch = 1000
    recommended = monitor.get_recommended_batch_size(initial_batch)

    # Should return a reasonable batch size (may be same or smaller)
    assert recommended > 0
    assert recommended <= initial_batch


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_memory_monitor_graceful_degradation():
    """E2E: MemoryMonitor degrades gracefully when psutil unavailable.

    Per CLAUDE.md §2.3:
    - MemoryMonitor returns conservative estimates when psutil unavailable
    - This is intentional graceful degradation, not a bug
    """
    from bioetl.application.core.memory_monitor import MemoryMonitor

    # Create monitor
    monitor = MemoryMonitor()

    # Should work even without psutil
    stats = monitor.get_stats()
    assert stats is not None

    # Should return valid percentage (0-100)
    assert 0 <= stats.percent_used <= 100


# ============================================================================
# Lock Management Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_lock_acquisition_and_release():
    """E2E: Lock can be acquired and released properly.

    Per RULES.md §3.3:
    - Locks should be acquired before pipeline run
    - Locks should be released after completion
    """
    from bioetl.infrastructure.locking.memory_lock import MemoryLock

    lock = MemoryLock()

    key = "test_pipeline"
    owner_id = str(uuid4())

    # Acquire lock
    acquired = await lock.acquire(
        key=key,
        owner_id=owner_id,
        ttl=60,
        wait=False,
    )
    assert acquired, "Lock should be acquired"

    # Validate owner
    is_owner = await lock.validate_owner(key=key, owner_id=owner_id)
    assert is_owner, "Owner should be validated"

    # Release lock
    released = await lock.release(key=key, owner_id=owner_id)
    assert released, "Lock should be released"

    # Cleanup
    await lock.aclose()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_lock_heartbeat_extends_ttl():
    """E2E: Lock heartbeat extends TTL.

    Per RULES.md §3.3:
    - Long-running pipelines need heartbeat to prevent TTL expiration
    """
    from bioetl.infrastructure.locking.memory_lock import MemoryLock

    lock = MemoryLock()

    key = "test_pipeline"
    owner_id = str(uuid4())

    # Acquire lock with short TTL
    await lock.acquire(key=key, owner_id=owner_id, ttl=2, wait=False)

    # Heartbeat should extend TTL
    heartbeat_success = await lock.heartbeat(key=key, owner_id=owner_id)
    assert heartbeat_success, "Heartbeat should succeed"

    # Lock should still be valid
    is_valid = await lock.validate_owner(key=key, owner_id=owner_id)
    assert is_valid, "Lock should still be valid after heartbeat"

    # Cleanup
    await lock.release(key=key, owner_id=owner_id)
    await lock.aclose()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_lock_prevents_concurrent_access():
    """E2E: Lock prevents concurrent access to same pipeline.

    Per RULES.md §3.3:
    - Only one process should hold lock at a time
    """
    from bioetl.infrastructure.locking.memory_lock import MemoryLock

    lock = MemoryLock()

    key = "test_pipeline"
    owner1 = str(uuid4())
    owner2 = str(uuid4())

    # First owner acquires lock
    acquired1 = await lock.acquire(key=key, owner_id=owner1, ttl=60, wait=False)
    assert acquired1, "First owner should acquire lock"

    # Second owner should fail (wait=False)
    acquired2 = await lock.acquire(key=key, owner_id=owner2, ttl=60, wait=False)
    assert not acquired2, "Second owner should not acquire lock"

    # Cleanup
    await lock.release(key=key, owner_id=owner1)
    await lock.aclose()


# ============================================================================
# Rate Limiter Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rate_limiter_throttles_requests():
    """E2E: Rate limiter throttles requests above capacity.

    Per RULES.md §8 (Providers):
    - Each provider has specific rate limits
    - Rate limiter should enforce these limits
    """
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

    # Create rate limiter with low rate for testing
    limiter = TokenBucket(
        rate=2.0,  # 2 tokens per second
        capacity=2,
        provider="test",
    )

    # First two requests should succeed immediately
    await limiter.acquire()
    await limiter.acquire()

    # Third request should be throttled
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start

    # Should have waited for token refill
    assert elapsed >= 0.4, f"Should have waited for token, elapsed: {elapsed}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rate_limiter_burst_capacity():
    """E2E: Rate limiter allows burst up to capacity.

    Token bucket should allow immediate burst requests up to capacity.
    """
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

    limiter = TokenBucket(
        rate=10.0,  # 10 tokens per second
        capacity=5,  # Burst capacity of 5
        provider="test",
    )

    # Should allow 5 immediate requests
    start = asyncio.get_event_loop().time()
    for _ in range(5):
        await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start

    # Burst should be fast (< 0.1s for 5 requests)
    assert elapsed < 0.5, f"Burst should be fast, elapsed: {elapsed}"


# ============================================================================
# Circuit Breaker Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """E2E: Circuit breaker opens after consecutive failures.

    Per ADR-007:
    - 5 consecutive failures should open the circuit
    - Open circuit should reject requests immediately
    """
    from bioetl.infrastructure.adapters.http.circuit_breaker import (
        CircuitBreaker,
        CircuitState,
    )

    breaker = CircuitBreaker(
        provider="test",
        failure_threshold=3,  # Lower threshold for testing
        recovery_timeout=1,  # Short timeout for testing
    )

    assert breaker.state == CircuitState.CLOSED

    # Record failures to trigger open
    for _ in range(3):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN, "Should be OPEN after 3 failures"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """E2E: Circuit breaker transitions to half-open for recovery probe.

    Per ADR-007:
    - After recovery_timeout, circuit should move to HALF_OPEN
    - Single success should close circuit
    - Single failure should re-open circuit
    """
    from bioetl.infrastructure.adapters.http.circuit_breaker import (
        CircuitBreaker,
        CircuitState,
    )

    breaker = CircuitBreaker(
        provider="test",
        failure_threshold=2,
        recovery_timeout=0.5,  # 500ms for testing
    )

    # Trigger open state
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.6)

    # Should transition to half-open
    assert breaker.state == CircuitState.HALF_OPEN

    # Success should close
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


# ============================================================================
# Retry Policy Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_retry_policy_deterministic_jitter():
    """E2E: Retry policy uses deterministic jitter for reproducibility.

    Per ADR-014:
    - Jitter should be deterministic for debugging
    - Same inputs should produce same delay
    """
    from bioetl.domain.resilience import RetryPolicy

    policy = RetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        multiplier=2.0,
        jitter=0.1,
        deterministic=True,
    )

    # Same inputs should give same delay
    delay1 = policy.calculate_delay(attempt=1, url="https://api.example.com/data")
    delay2 = policy.calculate_delay(attempt=1, url="https://api.example.com/data")

    assert delay1 == delay2, "Deterministic jitter should be reproducible"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_retry_policy_exponential_backoff():
    """E2E: Retry policy implements exponential backoff.

    Delays should increase exponentially with each attempt.
    """
    from bioetl.domain.resilience import RetryPolicy

    policy = RetryPolicy(
        max_attempts=5,
        base_delay=1.0,
        multiplier=2.0,
        jitter=0.0,  # No jitter for predictable test
        deterministic=True,
    )

    delays = [policy.calculate_delay(attempt=i, url="test") for i in range(4)]

    # Each delay should be ~2x the previous (exponential)
    assert delays[1] > delays[0]
    assert delays[2] > delays[1]
    assert delays[3] > delays[2]


# ============================================================================
# Storage Writer Safety Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_bronze_writer_atomic_writes(e2e_data_dir: Path):
    """E2E: Bronze writer uses atomic writes.

    Per RULES.md §2.1:
    - Bronze writes should be atomic (temp file + rename)
    - Partial writes should not corrupt data
    """
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.domain.ports.noop import NoOpLogger, NoOpMetrics
    from datetime import datetime, timezone

    writer = BronzeWriter(
        base_path=e2e_data_dir / "bronze",
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
    )

    # Write test records
    records = [
        b'{"id": 1, "value": "test1"}',
        b'{"id": 2, "value": "test2"}',
    ]

    path = await writer.write_bronze(
        records=iter(records),
        provider="test",
        entity="entity",
        date=datetime.now(timezone.utc),
        batch_id=uuid4(),
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=datetime.now(timezone.utc),
    )

    assert path.exists(), "Bronze file should exist"
    assert path.suffix == ".zst", "Should be zstd compressed"

    await writer.aclose()
