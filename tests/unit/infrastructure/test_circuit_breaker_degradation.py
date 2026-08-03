# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for CircuitBreakerGuard degradation scenarios.

These tests cover degradation patterns NOT covered by existing tests:
- Flapping behavior (rapid OPEN/CLOSED alternation)
- Sustained partial failure patterns
- Recovery under load
- Multiple consecutive trips
- Mixed error types during degradation
- Concurrent half-open probe race conditions
- Timeout boundary conditions
- Graceful degradation when metrics unavailable

Per ADR-007 and RULES.md §4.3.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    CircuitBreakerGuard,
    is_circuit_breaker_error,
)


async def _yield_once() -> None:
    """Exercise async paths in test doubles."""
    await asyncio.sleep(0)


class TestFlappingBehavior:
    """Tests for circuit breaker flapping (rapid state changes)."""

    @pytest.mark.unit
    async def test_rapid_open_close_cycles(self) -> None:
        """Flapping: Circuit can open and close multiple times rapidly.

        Scenario: Provider intermittently recovers and fails.
        Expected: Circuit tracks trips correctly through multiple cycles.
        """
        cb = CircuitBreakerGuard(
            provider="flapping_provider",
            failure_threshold=2,
            recovery_timeout=0,  # Immediate recovery for testing
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("Provider error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Perform 5 cycles of: fail until open, recover, repeat
        for cycle in range(5):
            # Fail until open
            for _ in range(2):
                with pytest.raises(RuntimeError):
                    await cb.call(fail)

            assert cb.get_state() == CircuitBreakerState.OPEN
            assert cb.get_trips_total() == cycle + 1

            # recovery_timeout=0 means the next probe can run immediately
            result = await cb.call(succeed)
            assert result == "ok"
            assert cb.get_state() == CircuitBreakerState.CLOSED

        # After 5 cycles, should have 5 trips
        assert cb.get_trips_total() == 5

    @pytest.mark.unit
    async def test_flapping_metrics_accumulation(self) -> None:
        """Flapping: Metrics correctly track all state transitions.

        Expected: Each trip increments counter, state gauge updates for each transition.
        """
        mock_metrics = MagicMock(spec=MetricsPort)
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
            metrics=mock_metrics,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Initial state emitted
        initial_calls = mock_metrics.set_gauge.call_count

        # First cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        await cb.call(succeed)

        # Should have multiple gauge calls (CLOSED, OPEN, HALF_OPEN, CLOSED)
        assert mock_metrics.set_gauge.call_count > initial_calls
        # Should have one trip counter increment (plus failure/success counters)
        trip_calls = [
            c
            for c in mock_metrics.increment_counter.call_args_list
            if c[0][0] == "bioetl_circuit_breaker_trips_total"
        ]
        assert len(trip_calls) == 1

    @pytest.mark.unit
    async def test_flapping_with_probe_failures(self) -> None:
        """Flapping: Half-open probe failures extend open period.

        Scenario: Provider fails during recovery probe multiple times.
        Expected: Each probe failure reopens circuit and increments trips.
        """
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Initial open
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_trips_total() == 1

        # 3 failed recovery probes
        for probe_attempt in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
            assert cb.get_state() == CircuitBreakerState.OPEN
            assert cb.get_trips_total() == probe_attempt + 2


class TestSustainedPartialFailure:
    """Tests for sustained partial failure patterns."""

    @pytest.mark.unit
    async def test_intermittent_failures_below_threshold(self) -> None:
        """Partial failure: Intermittent failures below threshold keep circuit closed.

        Pattern: fail-fail-succeed-fail-fail-succeed (never 3 consecutive)
        Expected: Circuit stays CLOSED.
        """
        cb = CircuitBreakerGuard(provider="test", failure_threshold=3)

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Pattern: 2 fails, 1 success, 2 fails, 1 success
        for _ in range(5):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
            with pytest.raises(RuntimeError):
                await cb.call(fail)
            await cb.call(succeed)  # Resets failure count

        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_trips_total() == 0

    @pytest.mark.unit
    async def test_degraded_service_pattern(self) -> None:
        """Partial failure: 60% failure rate but never consecutive threshold.

        Simulates degraded service that fails often but with successful responses
        interspersed, preventing circuit from opening.
        """
        cb = CircuitBreakerGuard(provider="test", failure_threshold=5)

        failures = 0
        successes = 0

        async def sometimes_fail(should_fail: bool) -> str:
            await _yield_once()
            if should_fail:
                raise RuntimeError("error")
            return "ok"

        # 100 requests with 60% failure rate, but max 4 consecutive failures
        pattern = [True, True, True, True, False] * 20  # 80% fail, 20% success

        for should_fail in pattern:
            try:
                await cb.call(lambda sf=should_fail: sometimes_fail(sf))
                successes += 1
            except RuntimeError:
                failures += 1

        # Circuit should stay closed despite high failure rate
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert failures > successes  # Confirms high failure rate


class TestRecoveryUnderLoad:
    """Tests for circuit breaker behavior during recovery with pending requests."""

    @pytest.mark.unit
    async def test_concurrent_requests_during_half_open(self) -> None:
        """Recovery: Only one probe request allowed during HALF_OPEN.

        When circuit transitions to HALF_OPEN, only one request should be allowed
        as probe; others should be blocked until probe completes.
        """
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        # Due to lock, concurrent calls are serialized
        # First will be probe, subsequent behavior depends on probe result
        probe_started = asyncio.Event()
        probe_complete = asyncio.Event()

        async def slow_probe() -> str:
            probe_started.set()
            await probe_complete.wait()
            return "ok"

        # Start probe
        probe_task = asyncio.create_task(cb.call(slow_probe))

        # Wait for probe to start
        await asyncio.wait_for(probe_started.wait(), timeout=1.0)

        # Complete probe successfully
        probe_complete.set()
        await probe_task

        # Circuit should be CLOSED now
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_burst_after_recovery(self) -> None:
        """Recovery: Burst of requests after circuit closes should work.

        After successful recovery probe, pending requests should proceed normally.
        """
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Open and recover
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        await cb.call(succeed)

        # Burst of concurrent requests
        results = await asyncio.gather(*[cb.call(succeed) for _ in range(20)])

        assert all(r == "ok" for r in results)
        assert cb.get_state() == CircuitBreakerState.CLOSED


class TestMultipleConsecutiveTrips:
    """Tests for multiple consecutive circuit trips."""

    @pytest.mark.unit
    async def test_progressive_degradation_pattern(self) -> None:
        """Consecutive trips: Each trip correctly increments counter.

        Simulates progressively degrading service that fails, recovers briefly,
        then fails again.
        """
        cb = CircuitBreakerGuard(
            provider="degrading_service",
            failure_threshold=3,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        expected_trips = 0

        for _cycle in range(10):
            # Fail until open
            for _ in range(3):
                with pytest.raises(RuntimeError):
                    await cb.call(fail)

            expected_trips += 1
            assert cb.get_state() == CircuitBreakerState.OPEN
            assert cb.get_trips_total() == expected_trips

            # recovery_timeout=0 means the next probe can run immediately
            await cb.call(succeed)
            assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_trips_counter_never_decreases(self) -> None:
        """Consecutive trips: Trip counter only increases, never decreases.

        Reset() should not affect trips_total counter.
        """
        cb = CircuitBreakerGuard(
            provider="test", failure_threshold=2, recovery_timeout=0
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Trip the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_trips_total() == 1

        # Manual reset
        cb.reset()
        assert cb.get_trips_total() == 1  # Counter preserved

        # Trip again
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_trips_total() == 2


class TestMixedErrorTypesDuringDegradation:
    """Tests for mixed error types during degradation."""

    @pytest.mark.unit
    async def test_4xx_errors_dont_affect_failure_count(self) -> None:
        """Mixed errors: 4xx errors (except 429) don't contribute to failure count.

        Only infrastructure errors should count toward threshold.
        """
        # is_circuit_breaker_error determines what counts
        request = httpx.Request("GET", "https://example.com")

        # 404 should NOT trigger breaker
        response_404 = httpx.Response(404, request=request)
        error_404 = httpx.HTTPStatusError(
            "Not found", request=request, response=response_404
        )
        assert is_circuit_breaker_error(error_404) is False

        # 500 SHOULD trigger breaker
        response_500 = httpx.Response(500, request=request)
        error_500 = httpx.HTTPStatusError(
            "Server error", request=request, response=response_500
        )
        assert is_circuit_breaker_error(error_500) is True

        # 429 SHOULD trigger breaker
        response_429 = httpx.Response(429, request=request)
        error_429 = httpx.HTTPStatusError(
            "Rate limited", request=request, response=response_429
        )
        assert is_circuit_breaker_error(error_429) is True

    @pytest.mark.unit
    async def test_mixed_5xx_and_4xx_sequence(self) -> None:
        """Mixed errors: Sequence of 5xx and 4xx correctly handles each type.

        Pattern: 500, 404, 500, 401, 500 -> only 3 x 500 count, but circuit
        breaker counts all exceptions passed to it, not classifying internally.

        Note: CircuitBreakerGuard.call() doesn't distinguish errors - it counts all.
        Error classification happens at HTTP client level before calling circuit.
        """
        cb = CircuitBreakerGuard(provider="test", failure_threshold=3)

        failure_count_before = cb.get_failure_count()

        async def raise_error() -> None:
            await _yield_once()
            raise RuntimeError("any error")

        # Any exception counts
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(raise_error)

        assert cb.get_failure_count() == failure_count_before + 2
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_business_errors_do_not_trip_breaker(self) -> None:
        """Business errors (ValueError) must NOT trip the circuit breaker.

        After RF-001, CALL_OPERATION_ERRORS only includes transient infrastructure
        errors. Programming/business errors propagate without affecting CB state.
        """
        cb = CircuitBreakerGuard(provider="test", failure_threshold=2)

        async def business_error() -> None:
            await _yield_once()
            raise ValueError("Invalid data")

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(business_error)

        # Circuit stays CLOSED — ValueError is not a transient error
        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0


class TestConcurrentHalfOpenProbes:
    """Tests for race conditions during HALF_OPEN state."""

    @pytest.mark.unit
    async def test_lock_serializes_state_transitions(self) -> None:
        """Concurrent probes: Lock ensures only one state transition at a time.

        Multiple concurrent calls during HALF_OPEN should be serialized.
        """
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        # Multiple concurrent probes
        async def probe() -> str:
            await _yield_once()
            return "ok"

        # Start multiple probes concurrently
        results = await asyncio.gather(
            cb.call(probe),
            cb.call(probe),
            cb.call(probe),
            return_exceptions=True,
        )

        # All should succeed (serialized by lock)
        successes = [r for r in results if r == "ok"]

        # First succeeds and closes circuit, subsequent may also succeed
        assert len(successes) >= 1
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_rapid_concurrent_half_open_attempts(self) -> None:
        """Concurrent probes: High concurrency during recovery maintains consistency."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        # 50 concurrent recovery attempts
        tasks = [asyncio.create_task(cb.call(succeed)) for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed after circuit closes
        successes = [r for r in results if r == "ok"]
        assert len(successes) == 50
        assert cb.get_state() == CircuitBreakerState.CLOSED


class TestTimeoutBoundaryConditions:
    """Tests for timeout edge cases and boundary conditions."""

    @pytest.mark.unit
    async def test_exact_recovery_timeout(self) -> None:
        """Timeout: Request at exact recovery timeout boundary.

        Request exactly at recovery_timeout should transition to HALF_OPEN.
        """
        recovery_timeout = 0.1
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=recovery_timeout,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Simulate the timeout window elapsing without a real wait.
        cb._last_failure_time -= recovery_timeout + 0.01

        # Should transition to HALF_OPEN and then CLOSED
        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_request_just_before_timeout(self) -> None:
        """Timeout: Request just before recovery timeout should be blocked."""
        # Use larger timeout (1s) for robustness against timer precision variance
        # (especially on Windows where timer resolution is ~15.6ms)
        recovery_timeout = 1.0
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=recovery_timeout,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        # Simulate 25% of recovery timeout having elapsed.
        cb._last_failure_time -= recovery_timeout * 0.25

        # Should still be blocked
        async def probe() -> str:
            await _yield_once()
            return "ok"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(probe)

        # retry_after should be positive (time remaining)
        assert exc_info.value.retry_after > 0
        assert exc_info.value.retry_after < recovery_timeout

    @pytest.mark.unit
    async def test_retry_after_decreases_over_time(self) -> None:
        """Timeout: retry_after decreases as time passes."""
        recovery_timeout = 1.0
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=recovery_timeout,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        # Open circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        async def probe() -> str:
            await _yield_once()
            return "ok"

        # First attempt
        with pytest.raises(CircuitBreakerOpenError) as exc1:
            await cb.call(probe)

        retry_after_1 = exc1.value.retry_after

        # Simulate more elapsed time before the second attempt.
        cb._last_failure_time -= 0.2

        # Second attempt
        with pytest.raises(CircuitBreakerOpenError) as exc2:
            await cb.call(probe)

        retry_after_2 = exc2.value.retry_after

        # retry_after should have decreased
        assert retry_after_2 < retry_after_1
        assert retry_after_2 < recovery_timeout


class TestGracefulDegradationWithoutMetrics:
    """Tests for circuit breaker operation without metrics."""

    @pytest.mark.unit
    async def test_all_operations_work_without_metrics(self) -> None:
        """No metrics: All operations succeed when metrics=None."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
            metrics=None,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Test normal operation
        result = await cb.call(succeed)
        assert result == "ok"

        # Test failure counting
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Test recovery
        result = await cb.call(succeed)
        assert result == "ok"

        # Test manual operations
        cb.force_open()
        assert cb.get_state() == CircuitBreakerState.OPEN

        cb.reset()
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_trips_tracking_without_metrics(self) -> None:
        """No metrics: Trip counting works correctly without metrics."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
            metrics=None,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        # Multiple trip cycles
        for cycle in range(3):
            for _ in range(2):
                with pytest.raises(RuntimeError):
                    await cb.call(fail)

            assert cb.get_trips_total() == cycle + 1

            await cb.call(succeed)

        assert cb.get_trips_total() == 3


class TestErrorClassificationCompleteness:
    """Tests for comprehensive error classification."""

    @pytest.mark.unit
    def test_all_5xx_status_codes_trigger(self) -> None:
        """Classification: All 5xx status codes trigger circuit breaker."""
        request = httpx.Request("GET", "https://example.com")

        for status_code in range(500, 512):
            response = httpx.Response(status_code, request=request)
            error = httpx.HTTPStatusError(
                f"Error {status_code}", request=request, response=response
            )
            assert is_circuit_breaker_error(error) is True, (
                f"Status {status_code} should trigger"
            )

    @pytest.mark.unit
    def test_all_4xx_except_429_dont_trigger(self) -> None:
        """Classification: 4xx status codes (except 429) don't trigger."""
        request = httpx.Request("GET", "https://example.com")

        for status_code in range(400, 429):
            response = httpx.Response(status_code, request=request)
            error = httpx.HTTPStatusError(
                f"Error {status_code}", request=request, response=response
            )
            assert is_circuit_breaker_error(error) is False, (
                f"Status {status_code} should NOT trigger"
            )

        for status_code in range(430, 452):
            response = httpx.Response(status_code, request=request)
            error = httpx.HTTPStatusError(
                f"Error {status_code}", request=request, response=response
            )
            assert is_circuit_breaker_error(error) is False, (
                f"Status {status_code} should NOT trigger"
            )

    @pytest.mark.unit
    def test_httpx_timeout_variants_trigger(self) -> None:
        """Classification: All httpx timeout variants trigger circuit breaker."""
        assert is_circuit_breaker_error(httpx.ConnectTimeout("Timeout")) is True
        assert is_circuit_breaker_error(httpx.ReadTimeout("Timeout")) is True
        assert is_circuit_breaker_error(httpx.ConnectError("Connection failed")) is True

    @pytest.mark.unit
    def test_generic_exceptions_dont_trigger(self) -> None:
        """Classification: Generic exceptions don't trigger circuit breaker."""
        assert is_circuit_breaker_error(ValueError("Invalid")) is False
        assert is_circuit_breaker_error(TypeError("Wrong type")) is False
        assert is_circuit_breaker_error(RuntimeError("Runtime error")) is False
        assert is_circuit_breaker_error(KeyError("Missing key")) is False


class TestStateInvariantsUnderStress:
    """Tests for state machine invariants under stress conditions."""

    @pytest.mark.unit
    async def test_state_always_valid(self) -> None:
        """Stress: State is always one of the valid enum values."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=3,
            recovery_timeout=0,
        )

        valid_states = {
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        }

        async def random_operation(op: int) -> str:
            await _yield_once()
            if op % 3 == 0:
                raise RuntimeError("error")
            return "ok"

        # Random sequence of operations
        for i in range(100):
            try:
                await cb.call(lambda i=i: random_operation(i))
            except (RuntimeError, CircuitBreakerOpenError):
                continue

            # State should always be valid
            assert cb.get_state() in valid_states

        # Final state should be valid
        assert cb.get_state() in valid_states

    @pytest.mark.unit
    async def test_failure_count_never_negative(self) -> None:
        """Stress: Failure count is never negative."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=5,
            recovery_timeout=0,
        )

        async def sometimes_fail(should_fail: bool) -> str:
            await _yield_once()
            if should_fail:
                raise RuntimeError("error")
            return "ok"

        for i in range(50):
            try:
                await cb.call(lambda i=i: sometimes_fail(i % 2 == 0))
            except (RuntimeError, CircuitBreakerOpenError):
                continue

            # Failure count should never be negative
            assert cb.get_failure_count() >= 0

    @pytest.mark.unit
    async def test_trips_total_monotonically_increases(self) -> None:
        """Stress: trips_total only increases, never decreases."""
        cb = CircuitBreakerGuard(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail() -> None:
            await _yield_once()
            raise RuntimeError("error")

        async def succeed() -> str:
            await _yield_once()
            return "ok"

        previous_trips = 0

        for _ in range(20):
            # Random failure pattern
            for _ in range(2):
                with pytest.raises(RuntimeError):
                    await cb.call(fail)

            current_trips = cb.get_trips_total()
            assert current_trips >= previous_trips
            previous_trips = current_trips

            # Recovery
            await cb.call(succeed)
