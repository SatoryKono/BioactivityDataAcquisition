# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Property-based tests for port contracts using Hypothesis.

These tests use property-based testing to verify that port implementations
maintain their contracts across a wide range of inputs and edge cases.

Implements the refactoring plan: "Расширение контрактных тестов портов".

Note: max_examples is controlled by Hypothesis profile (conftest.py):
- CI: 10 examples (fast)
- fast: 5 examples (smoke tests)
- dev: 50 examples (default)
- thorough: 200 examples (pre-release)

Tests do NOT override max_examples to respect profile settings.
"""

from __future__ import annotations

import asyncio
from typing import Any
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bioetl.domain import ports

# Mark all tests in this module as slow and hypothesis-based
pytestmark = [pytest.mark.slow, pytest.mark.hypothesis, pytest.mark.architecture]


def run_async(coro) -> Any:
    """Run async coroutine in sync context for hypothesis tests."""
    return asyncio.run(coro)


# ============================================================================
# Hypothesis Strategies for Port Testing
# ============================================================================


# Strategy for valid lock keys (non-empty strings)
lock_key_strategy = st.text(
    min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N"))
).filter(lambda x: x.strip() != "")

# Windows reserved names that cannot be used as file/directory names
# See: https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "com2",
        "com3",
        "com4",
        "com5",
        "com6",
        "com7",
        "com8",
        "com9",
        "lpt1",
        "lpt2",
        "lpt3",
        "lpt4",
        "lpt5",
        "lpt6",
        "lpt7",
        "lpt8",
        "lpt9",
    }
)

# Strategy for valid pipeline names (lowercase alphanumeric with underscores)
# Uses lowercase only to avoid case-sensitivity issues on Windows file system
# Filters out Windows reserved names to avoid filesystem errors
pipeline_name_strategy = st.from_regex(r"[a-z][a-z0-9_]{0,49}", fullmatch=True).filter(
    lambda name: name not in _WINDOWS_RESERVED_NAMES
)

# Strategy for TTL values (positive integers within reasonable range)
ttl_strategy = st.integers(min_value=1, max_value=3600)

# Strategy for checkpoint metadata (JSON-serializable dictionaries)
json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10000, max_value=10000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
    st.text(max_size=100),
)

checkpoint_metadata_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
    values=json_primitive,
    max_size=10,
)

# Strategy for rate limiter configuration
rate_strategy = st.floats(min_value=0.1, max_value=1000.0)
capacity_strategy = st.integers(min_value=1, max_value=1000)

# Strategy for circuit breaker configuration
failure_threshold_strategy = st.integers(min_value=1, max_value=100)
recovery_timeout_strategy = st.integers(min_value=1, max_value=600)


# ============================================================================
# LockPort Property-Based Tests
# ============================================================================


class TestLockPortProperties:
    """Property-based tests for LockPort contract invariants."""

    @given(key=lock_key_strategy)
    @settings(deadline=None)
    def test_acquire_release_cycle_is_consistent(self, key: str) -> None:
        """Property: acquire() followed by release() MUST succeed for same owner."""
        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        async def test_cycle():
            lock = MemoryLock()
            owner = deterministic_uuid_from_callsite("test_port_contracts_hypothesis")

            try:
                acquired = await lock.acquire(key, owner)
                assert acquired, f"Failed to acquire lock for key: {key!r}"

                is_owner = await lock.validate_owner(key, owner)
                assert is_owner, f"Owner validation failed for key: {key!r}"

                released = await lock.release(key, owner)
                assert released, f"Failed to release lock for key: {key!r}"

                # After release, validate_owner should return False
                is_owner_after = await lock.validate_owner(key, owner)
                assert not is_owner_after, "Lock still valid after release"
            finally:
                await lock.aclose()

        asyncio.run(test_cycle())

    @given(key=lock_key_strategy, ttl=ttl_strategy)
    @settings(deadline=None)
    def test_heartbeat_extends_ttl(self, key: str, ttl: int) -> None:
        """Property: heartbeat() on valid lock MUST return True."""
        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        async def test_heartbeat():
            lock = MemoryLock()
            owner = deterministic_uuid_from_callsite("test_port_contracts_hypothesis")

            try:
                # Acquire with TTL
                acquired = await lock.acquire(key, owner, ttl=ttl)
                assert acquired

                # Heartbeat should succeed
                result = await lock.heartbeat(key, owner)
                assert result, f"Heartbeat failed for key: {key!r}, ttl: {ttl}"

                # Lock should still be valid
                is_owner = await lock.validate_owner(key, owner)
                assert is_owner
            finally:
                await lock.aclose()

        asyncio.run(test_heartbeat())

    @given(keys=st.lists(lock_key_strategy, min_size=1, max_size=10, unique=True))
    @settings(deadline=None)
    def test_multiple_locks_are_independent(self, keys: list[str]) -> None:
        """Property: Locks on different keys MUST be independent."""
        from bioetl.infrastructure.locking.memory_lock import MemoryLock

        async def test_independence():
            lock = MemoryLock()
            owners = [
                deterministic_uuid_from_callsite("test_port_contracts_hypothesis")
                for _ in keys
            ]

            try:
                # Acquire all locks
                for key, owner in zip(keys, owners, strict=True):
                    acquired = await lock.acquire(key, owner)
                    assert acquired, f"Failed to acquire lock for key: {key!r}"

                # Verify all locks are held by correct owners
                for key, owner in zip(keys, owners, strict=True):
                    is_owner = await lock.validate_owner(key, owner)
                    assert is_owner, f"Wrong owner for key: {key!r}"

                # Release in reverse order - should not affect others
                for key, owner in reversed(list(zip(keys, owners, strict=True))):
                    released = await lock.release(key, owner)
                    assert released
            finally:
                await lock.aclose()

        asyncio.run(test_independence())


# ============================================================================
# CheckpointPort Property-Based Tests
# ============================================================================


class TestCheckpointPortProperties:
    """Property-based tests for CheckpointPort contract invariants."""

    @given(pipeline=pipeline_name_strategy, metadata=checkpoint_metadata_strategy)
    @settings(deadline=None)
    def test_save_load_roundtrip_preserves_data(
        self, pipeline: str, metadata: dict[str, Any]
    ) -> None:
        """Property: save() followed by load() preserves caller metadata."""
        import tempfile

        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        async def test_roundtrip():
            with tempfile.TemporaryDirectory() as tmp_dir:
                checkpoint = LocalCheckpointAdapter(base_path=tmp_dir)
                run_id = deterministic_uuid_from_callsite(
                    "test_port_contracts_hypothesis"
                )

                try:
                    await checkpoint.save(pipeline, run_id, metadata)
                    result = await checkpoint.load(pipeline)

                    assert result is not None, f"Failed to load checkpoint: {pipeline}"
                    loaded_run_id, loaded_metadata = result

                    assert loaded_run_id == run_id, "Run ID mismatch after roundtrip"
                    for key, expected_value in metadata.items():
                        assert loaded_metadata[key] == expected_value, (
                            "Caller metadata mismatch after roundtrip"
                        )

                    extra_keys = set(loaded_metadata) - set(metadata)
                    assert extra_keys <= {"checkpoint_saved_at_epoch_seconds"}
                    if "checkpoint_saved_at_epoch_seconds" not in metadata:
                        assert isinstance(
                            loaded_metadata["checkpoint_saved_at_epoch_seconds"],
                            float,
                        )
                finally:
                    await checkpoint.aclose()

        asyncio.run(test_roundtrip())

    @given(
        pipelines=st.lists(pipeline_name_strategy, min_size=1, max_size=10, unique=True)
    )
    @settings(deadline=None)
    def test_list_all_returns_all_saved_pipelines(self, pipelines: list[str]) -> None:
        """Property: list_all() MUST return all saved pipeline names."""
        import tempfile

        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        async def test_list():
            with tempfile.TemporaryDirectory() as tmp_dir:
                checkpoint = LocalCheckpointAdapter(base_path=tmp_dir)

                try:
                    # Save checkpoints for all pipelines
                    for pipeline in pipelines:
                        await checkpoint.save(
                            pipeline,
                            deterministic_uuid_from_callsite(
                                "test_port_contracts_hypothesis"
                            ),
                            {},
                        )

                    # List should return all pipelines
                    listed = await checkpoint.list_all()
                    assert set(listed) == set(pipelines), (
                        f"list_all() mismatch: expected {set(pipelines)}, got {set(listed)}"
                    )
                finally:
                    await checkpoint.aclose()

        asyncio.run(test_list())

    @given(pipeline=pipeline_name_strategy)
    @settings(deadline=None)
    def test_delete_makes_load_return_none(self, pipeline: str) -> None:
        """Property: delete() followed by load() MUST return None."""
        import tempfile

        from bioetl.infrastructure.checkpoint.local_checkpoint import (
            LocalCheckpointAdapter,
        )

        async def test_delete():
            with tempfile.TemporaryDirectory() as tmp_dir:
                checkpoint = LocalCheckpointAdapter(base_path=tmp_dir)

                try:
                    # Save and then delete
                    await checkpoint.save(
                        pipeline,
                        deterministic_uuid_from_callsite(
                            "test_port_contracts_hypothesis"
                        ),
                        {"test": "value"},
                    )
                    await checkpoint.delete(pipeline)

                    # Load should return None
                    result = await checkpoint.load(pipeline)
                    assert result is None, (
                        f"Load returned data after delete: {pipeline}"
                    )
                finally:
                    await checkpoint.aclose()

        asyncio.run(test_delete())


# ============================================================================
# RateLimiterPort Property-Based Tests
# ============================================================================


class TestRateLimiterPortProperties:
    """Property-based tests for RateLimiterPort contract invariants."""

    @given(rate=rate_strategy, capacity=capacity_strategy)
    @settings(deadline=None)
    def test_initial_tokens_equal_capacity(self, rate: float, capacity: int) -> None:
        """Property: Initial available_tokens() MUST equal capacity."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        # Available tokens should equal capacity at start
        available = bucket.available_tokens()
        assert available == capacity, (
            f"Initial tokens ({available}) != capacity ({capacity})"
        )

    @given(
        # Low rate to prevent token replenishment during test execution
        rate=st.floats(min_value=0.001, max_value=1.0),
        capacity=capacity_strategy,
    )
    @settings(deadline=None)
    def test_try_acquire_respects_capacity(self, rate: float, capacity: int) -> None:
        """Property: try_acquire() MUST fail after capacity tokens acquired.

        Uses low rate to ensure tokens aren't replenished during iteration.
        """
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        # Acquire all tokens
        for i in range(capacity):
            result = bucket.try_acquire()
            assert result, (
                f"try_acquire() failed at iteration {i} for capacity {capacity}"
            )

        # Next attempt should fail (rate is low enough that no replenishment occurs)
        result = bucket.try_acquire()
        assert not result, "try_acquire() succeeded after capacity exhausted"

    @given(
        rate=rate_strategy,
        capacity=st.integers(min_value=2, max_value=100),
        tokens=st.integers(min_value=1, max_value=10),
    )
    @settings(deadline=None)
    def test_acquire_multiple_tokens_works(
        self, rate: float, capacity: int, tokens: int
    ) -> None:
        """Property: acquire(n) MUST work when n <= capacity."""
        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        # Ensure tokens <= capacity
        tokens = min(tokens, capacity)
        bucket = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        async def test_acquire():
            await bucket.acquire(tokens=tokens)
            # Should succeed without exception
            remaining = bucket.available_tokens()
            assert remaining == capacity - tokens, (
                f"Wrong remaining tokens: {remaining} != {capacity - tokens}"
            )

        asyncio.run(test_acquire())

    @given(rate=rate_strategy, capacity=capacity_strategy)
    @settings(deadline=None)
    def test_tokens_never_exceed_capacity(self, rate: float, capacity: int) -> None:
        """Property: available_tokens() MUST never exceed capacity."""
        import time

        from bioetl.infrastructure.adapters.http.rate_limiter import (
            TokenBucketRateLimiter,
        )

        bucket = TokenBucketRateLimiter(rate=rate, capacity=capacity)

        # Simulate time passing by manipulating internal state
        bucket._last_refill = time.monotonic() - 100  # 100 seconds ago
        bucket._refill()

        available = bucket.available_tokens()
        assert available <= capacity, (
            f"Tokens ({available}) exceeded capacity ({capacity})"
        )


# ============================================================================
# CircuitBreakerPort Property-Based Tests
# ============================================================================


class TestCircuitBreakerPortProperties:
    """Property-based tests for CircuitBreakerPort contract invariants."""

    @given(
        failure_threshold=failure_threshold_strategy,
        recovery_timeout=recovery_timeout_strategy,
    )
    @settings(deadline=None)
    def test_initial_state_is_closed(
        self, failure_threshold: int, recovery_timeout: int
    ) -> None:
        """Property: Initial state MUST be CLOSED."""
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        assert breaker.get_state() == CircuitBreakerState.CLOSED, (
            f"Initial state is not CLOSED for threshold={failure_threshold}"
        )

    @given(
        failure_threshold=failure_threshold_strategy,
        recovery_timeout=recovery_timeout_strategy,
    )
    @settings(deadline=None)
    def test_reset_returns_to_closed(
        self, failure_threshold: int, recovery_timeout: int
    ) -> None:
        """Property: reset() MUST return state to CLOSED."""
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        # Force open
        breaker.force_open()
        assert breaker.get_state() == CircuitBreakerState.OPEN

        # Reset
        breaker.reset()
        assert breaker.get_state() == CircuitBreakerState.CLOSED
        assert breaker.get_failure_count() == 0

    @given(failure_threshold=st.integers(min_value=1, max_value=10))
    @settings(deadline=None)
    def test_opens_after_threshold_failures(self, failure_threshold: int) -> None:
        """Property: Circuit MUST open after failure_threshold consecutive failures."""
        from bioetl.domain.types import CircuitBreakerState
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreakerGuard,
        )

        breaker = CircuitBreakerGuard(
            provider="test",
            failure_threshold=failure_threshold,
            recovery_timeout=300,
        )

        async def failing_func():
            raise RuntimeError("Simulated failure")

        async def test_threshold():
            for _ in range(failure_threshold):
                try:
                    await breaker.call(failing_func)
                except RuntimeError:
                    pass

            assert breaker.get_state() == CircuitBreakerState.OPEN, (
                f"Circuit not open after {failure_threshold} failures"
            )

        asyncio.run(test_threshold())


# ============================================================================
# MetricsPort Property-Based Tests
# ============================================================================


class TestMetricsPortProperties:
    """Property-based tests for MetricsPort contract invariants."""

    @given(
        metric_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
        value=st.floats(min_value=-1e10, max_value=1e10, allow_nan=False),
    )
    @settings(deadline=None)
    def test_noop_metrics_accepts_any_valid_input(
        self, metric_name: str, value: float
    ) -> None:
        """Property: NoOpMetrics MUST accept any valid metric input without error."""
        from bioetl.domain.ports.noop import NoOpMetrics

        metrics = NoOpMetrics()

        # Should not raise for any valid input
        metrics.increment_counter(metric_name, 1, {})
        metrics.set_gauge(metric_name, value, {})
        metrics.observe_histogram(metric_name, abs(value), {})

    @given(
        labels=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),
            values=st.text(max_size=50),
            max_size=5,
        )
    )
    @settings(deadline=None)
    def test_noop_metrics_accepts_various_labels(self, labels: dict[str, str]) -> None:
        """Property: NoOpMetrics MUST accept various label combinations."""
        from bioetl.domain.ports.noop import NoOpMetrics

        metrics = NoOpMetrics()

        # Should not raise for any valid labels
        metrics.increment_counter("test_metric", 1, labels)
        metrics.set_gauge("test_metric", 1.0, labels)
        metrics.observe_histogram("test_metric", 1.0, labels)


# ============================================================================
# LoggerPort Property-Based Tests
# ============================================================================


class TestLoggerPortProperties:
    """Property-based tests for LoggerPort contract invariants."""

    @given(
        message=st.text(max_size=200),
        context=st.dictionaries(
            # Filter out Python reserved keywords that conflict with method parameters
            keys=st.text(min_size=1, max_size=20).filter(
                lambda x: x.strip() != "" and x not in ("self", "cls", "msg", "message")
            ),
            values=st.one_of(
                st.text(max_size=50), st.integers(), st.floats(allow_nan=False)
            ),
            max_size=5,
        ),
    )
    @settings(deadline=None)
    def test_noop_logger_accepts_any_message(
        self, message: str, context: dict[str, Any]
    ) -> None:
        """Property: NoOpLogger MUST accept any message and context."""
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        logger = NoOpLogger()

        # Should not raise for any input
        logger.info(message, **context)
        logger.warning(message, **context)
        logger.error(message, **context)
        logger.debug(message, **context)

    @given(
        bindings=st.dictionaries(
            # Filter out Python reserved keywords that conflict with method parameters
            keys=st.text(min_size=1, max_size=20).filter(
                lambda x: x.strip() != "" and x not in ("self", "cls")
            ),
            values=st.one_of(st.text(max_size=50), st.integers()),
            max_size=5,
        )
    )
    @settings(deadline=None)
    def test_logger_bind_returns_logger_port(self, bindings: dict[str, Any]) -> None:
        """Property: LoggerPort.bind() MUST return LoggerPort instance."""
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        logger = NoOpLogger()
        bound = logger.bind(**bindings)

        assert isinstance(bound, ports.LoggerPort), (
            "bind() MUST return LoggerPort instance"
        )


# ============================================================================
# TracingPort Property-Based Tests
# ============================================================================


class TestTracingPortProperties:
    """Property-based tests for TracingPort contract invariants."""

    tracing_attribute_value = st.one_of(
        st.booleans(),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
        st.text(max_size=80),
    )

    @given(
        tracer_name=st.text(min_size=1, max_size=80).filter(
            lambda value: value.strip() != ""
        ),
        span_name=st.text(min_size=1, max_size=80).filter(
            lambda value: value.strip() != ""
        ),
        attributes=st.dictionaries(
            keys=st.text(min_size=1, max_size=40).filter(
                lambda value: value.strip() != ""
            ),
            values=tracing_attribute_value,
            max_size=5,
        ),
    )
    @settings(deadline=None)
    def test_noop_tracing_accepts_valid_span_inputs(
        self,
        tracer_name: str,
        span_name: str,
        attributes: dict[str, object],
    ) -> None:
        """Property: NoOpTracing MUST preserve the OTel-like tracing surface."""
        from bioetl.domain.ports.noop import NoOpTracing

        tracing = NoOpTracing()
        tracer = tracing.get_tracer(tracer_name)

        with tracer.start_as_current_span(span_name, attributes=attributes) as span:
            for key, value in attributes.items():
                assert span.set_attribute(key, value) is None
            assert span.record_exception(RuntimeError("tracing-property")) is None

        assert isinstance(tracing, ports.TracingPort)
        assert tracing.flush() is None
        assert tracing.close() is None


# ============================================================================
# JsonEncoderPort Property-Based Tests
# ============================================================================


class TestJsonEncoderPortProperties:
    """Property-based tests for JsonEncoderPort contract invariants."""

    # Strategy for JSON-serializable data (avoiding problematic edge cases)
    json_safe_primitive = st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(
            allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10
        ),
        st.text(max_size=100),
    )

    json_safe_value = st.recursive(
        json_safe_primitive,
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(
                st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),
                children,
                max_size=5,
            ),
        ),
        max_leaves=10,
    )

    @given(data=json_safe_value)
    @settings(deadline=None)
    def test_dumps_loads_roundtrip(self, data: Any) -> None:
        """Property: dumps() followed by loads() MUST preserve data."""
        from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder

        encoder = StdLibJsonEncoder()

        json_str = encoder.dumps(data)
        loaded = encoder.loads(json_str)

        # Handle float comparison (floats may have small precision differences)
        if isinstance(data, float):
            assert abs(data - loaded) < 1e-10, (
                f"Float roundtrip failed: {data} != {loaded}"
            )
        else:
            assert data == loaded, f"Roundtrip failed: {data} != {loaded}"

    @given(
        data=st.dictionaries(
            st.text(min_size=1, max_size=20).filter(lambda x: x.strip() != ""),
            st.one_of(st.integers(), st.text(max_size=20)),
            min_size=1,
            max_size=10,
        )
    )
    @settings(deadline=None)
    def test_dumps_canonical_is_deterministic(self, data: dict[str, Any]) -> None:
        """Property: dumps_canonical() MUST produce identical output for same input."""
        from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder

        encoder = StdLibJsonEncoder()

        result1 = encoder.dumps_canonical(data)
        result2 = encoder.dumps_canonical(data)

        assert result1 == result2, (
            f"dumps_canonical() not deterministic:\n{result1}\n!=\n{result2}"
        )

    @given(
        data=st.dictionaries(
            st.text(min_size=1, max_size=10).filter(lambda x: x.strip() != ""),
            st.integers(),
            min_size=2,
            max_size=5,
        )
    )
    @settings(deadline=None)
    def test_dumps_canonical_sorts_keys(self, data: dict[str, Any]) -> None:
        """Property: dumps_canonical() MUST produce sorted keys."""
        from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder

        encoder = StdLibJsonEncoder()

        result = encoder.dumps_canonical(data)
        loaded = encoder.loads(result)

        # Keys in the JSON string should be in sorted order
        expected_keys = sorted(data.keys())
        actual_keys = list(loaded.keys())

        assert actual_keys == expected_keys, (
            f"Keys not sorted: {actual_keys} != {expected_keys}"
        )


# ============================================================================
# Memory Monitor Port Property-Based Tests
# ============================================================================


class TestMemoryMonitorPortProperties:
    """Property-based tests for MemoryMonitorPort contract invariants."""

    @given(batch_size=st.integers(min_value=1, max_value=10000))
    @settings(deadline=None)
    def test_recommended_batch_size_is_positive(self, batch_size: int) -> None:
        """Property: get_recommended_batch_size() MUST return positive integer."""
        from bioetl.domain.config import MemoryConfig
        from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor(config=MemoryConfig())

        recommended = monitor.get_recommended_batch_size(batch_size)
        assert recommended > 0, (
            f"Recommended batch size must be positive, got {recommended}"
        )

    @given(batch_size=st.integers(min_value=1, max_value=10000))
    @settings(deadline=None)
    def test_noop_monitor_returns_same_batch_size(self, batch_size: int) -> None:
        """Property: NoOpMemoryMonitor MUST return input batch size unchanged."""
        from bioetl.domain.ports.noop import NoOpMemoryMonitor

        monitor = NoOpMemoryMonitor()

        recommended = monitor.get_recommended_batch_size(batch_size)
        assert recommended == batch_size, (
            f"NoOpMemoryMonitor changed batch size: {batch_size} -> {recommended}"
        )

    @given(
        records_count=st.integers(min_value=0, max_value=100000),
        avg_record_size=st.integers(min_value=1, max_value=10000),
    )
    @settings(deadline=None)
    def test_estimate_batch_memory_is_non_negative(
        self, records_count: int, avg_record_size: int
    ) -> None:
        """Property: estimate_batch_memory_mb() MUST return non-negative value."""
        from bioetl.domain.config import MemoryConfig
        from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor(config=MemoryConfig())

        estimate = monitor.estimate_batch_memory_mb(records_count, avg_record_size)
        assert estimate >= 0, f"Memory estimate must be non-negative, got {estimate}"
