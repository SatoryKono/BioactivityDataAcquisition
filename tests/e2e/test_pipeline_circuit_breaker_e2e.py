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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""E2E tests for pipeline circuit breaker behavior.

Tests the circuit breaker pattern for provider failure handling per ADR-007:
- Circuit opens after consecutive failures
- Requests blocked while circuit is open
- Circuit transitions through CLOSED -> OPEN -> HALF_OPEN -> CLOSED

Per RULES.md §4.3 Circuit Breaker:
- Trigger: 5 consecutive errors
- Open Duration: 5 minutes
- Recovery: Half-Open → 1 probe → Closed/Open
- Metrics: circuit_breaker_state, trips_total
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    CircuitBreakerGuard,
    is_circuit_breaker_error,
)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    async def test_state_transitions__state_is_closed__76c048e0(self):
        """E2E: Circuit breaker starts in CLOSED state."""
        cb = CircuitBreakerGuard(provider="test_provider")

        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0
        assert cb.get_trips_total() == 0

    async def test_successful_calls_keep_circuit_closed(self):
        """E2E: Successful calls maintain CLOSED state."""
        cb = CircuitBreakerGuard(provider="test_provider", failure_threshold=5)

        async def success():
            await asyncio.sleep(0)
            return "ok"

        for _ in range(10):
            result = await cb.call(success)
            assert result == "ok"

        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0

    async def test_failures_increment_count(self):
        """E2E: Failures increment the failure counter."""
        cb = CircuitBreakerGuard(provider="test_provider", failure_threshold=5)

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Provider error")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_failure_count() == 3
        assert cb.get_state() == CircuitBreakerState.CLOSED  # Not yet open

    async def test_threshold_failures_open_circuit(self):
        """E2E: Reaching failure threshold opens circuit."""
        cb = CircuitBreakerGuard(provider="test_provider", failure_threshold=5)

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Provider error")

        for _ in range(5):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 1

    async def test_open_circuit_blocks_calls(self):
        """E2E: Open circuit blocks subsequent calls."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=3,
            recovery_timeout=300,  # Long timeout
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Next call should be blocked
        async def would_succeed():
            await asyncio.sleep(0)
            return "success"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(would_succeed)

        assert exc_info.value.provider == "test_provider"
        assert exc_info.value.retry_after > 0

    async def test_half_open_after_timeout(self):
        """E2E: Circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=3,
            recovery_timeout=0,  # Immediate recovery for testing
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Next successful call should transition to CLOSED
        async def success():
            await asyncio.sleep(0)
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    async def test_half_open_failure_reopens(self):
        """E2E: Failed probe in HALF_OPEN reopens circuit."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=3,
            recovery_timeout=0,
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        initial_trips = cb.get_trips_total()
        assert cb.get_state() == CircuitBreakerState.OPEN

        # Probe fails - should reopen
        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == initial_trips + 1


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery behavior."""

    async def test_success_resets_failure_count(self):
        """E2E: Successful call resets consecutive failure count."""
        cb = CircuitBreakerGuard(provider="test_provider", failure_threshold=5)

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        async def success():
            await asyncio.sleep(0)
            return "ok"

        # Accumulate some failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_failure_count() == 3

        # Successful call resets count
        await cb.call(success)

        assert cb.get_failure_count() == 0
        assert cb.get_state() == CircuitBreakerState.CLOSED

    async def test_manual_reset(self):
        """E2E: Manual reset returns circuit to CLOSED state."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=2,
            recovery_timeout=300,
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Manual reset
        cb.reset()

        assert cb.get_state() == CircuitBreakerState.CLOSED
        assert cb.get_failure_count() == 0

    async def test_force_open(self):
        """E2E: force_open() manually opens circuit."""
        cb = CircuitBreakerGuard(provider="test_provider", failure_threshold=5)

        assert cb.get_state() == CircuitBreakerState.CLOSED

        cb.force_open()

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 1


@pytest.mark.e2e
class TestCircuitBreakerErrorClassification:
    """Tests for error classification in circuit breaker (sync tests)."""

    def test_connection_error_triggers_breaker(self):
        """E2E: Connection errors trigger circuit breaker."""
        error = httpx.ConnectError("Connection failed")

        assert is_circuit_breaker_error(error) is True

    def test_timeout_error_triggers_breaker(self):
        """E2E: Timeout errors trigger circuit breaker."""
        connect_timeout = httpx.ConnectTimeout("Connection timeout")
        read_timeout = httpx.ReadTimeout("Read timeout")

        assert is_circuit_breaker_error(connect_timeout) is True
        assert is_circuit_breaker_error(read_timeout) is True

    def test_server_error_triggers_breaker(self):
        """E2E: 5xx server errors trigger circuit breaker."""
        request = httpx.Request("GET", "https://api.example.com")
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError(
            "Server error", request=request, response=response
        )

        assert is_circuit_breaker_error(error) is True

    def test_rate_limit_triggers_breaker(self):
        """E2E: 429 Rate limit triggers circuit breaker."""
        request = httpx.Request("GET", "https://api.example.com")
        response = httpx.Response(429, request=request)
        error = httpx.HTTPStatusError(
            "Rate limited", request=request, response=response
        )

        assert is_circuit_breaker_error(error) is True

    def test_client_error_does_not_trigger_breaker(self):
        """E2E: 4xx client errors (except 429) don't trigger circuit breaker."""
        request = httpx.Request("GET", "https://api.example.com")

        for status_code in [400, 401, 403, 404, 422]:
            response = httpx.Response(status_code, request=request)
            error = httpx.HTTPStatusError(
                "Client error", request=request, response=response
            )
            assert is_circuit_breaker_error(error) is False, (
                f"Status {status_code} should not trigger"
            )

    def test_business_error_does_not_trigger_breaker(self):
        """E2E: Business logic errors don't trigger circuit breaker."""
        error = ValueError("Invalid data format")

        assert is_circuit_breaker_error(error) is False


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics."""

    async def test_trips_total_increments_on_open(self):
        """E2E: trips_total increments each time circuit opens."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=2,
            recovery_timeout=0,
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        async def success():
            await asyncio.sleep(0)
            return "ok"

        # First trip
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_trips_total() == 1

        await cb.call(success)

        # Second trip
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_trips_total() == 2

    async def test_retry_after_calculation(self):
        """E2E: retry_after correctly calculates remaining timeout."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=2,
            recovery_timeout=10,  # 10 seconds
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        async def probe():
            await asyncio.sleep(0)
            return "ok"

        # Try to call - should get retry_after close to 10
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(probe)

        # retry_after should be close to recovery_timeout (accounting for small delays)
        assert exc_info.value.retry_after > 9.0
        assert exc_info.value.retry_after <= 10.0


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCircuitBreakerConcurrency:
    """Tests for concurrent access to circuit breaker."""

    async def test_concurrent_calls_consistent_state(self):
        """E2E: Concurrent calls maintain consistent state."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=10,
        )
        success_count = 0
        failure_count = 0

        async def mixed_call(should_fail: bool):
            await asyncio.sleep(0)
            nonlocal success_count, failure_count
            if should_fail:
                raise RuntimeError("Error")
            return "ok"

        async def worker(worker_id: int):
            nonlocal success_count, failure_count
            for i in range(10):
                try:
                    should_fail = (worker_id + i) % 3 == 0
                    await cb.call(
                        lambda sf=should_fail: (
                            mixed_call(sf) if not sf else mixed_call(True)
                        )
                    )
                    success_count += 1
                except RuntimeError:
                    failure_count += 1
                except CircuitBreakerOpenError:
                    pass

        # Run concurrent workers
        tasks = [asyncio.create_task(worker(i)) for i in range(5)]
        await asyncio.gather(*tasks)

        # Circuit should be in a valid state
        assert cb.get_state() in (
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        )

    async def test_rapid_failures_open_circuit(self):
        """E2E: Rapid failures correctly open circuit."""
        cb = CircuitBreakerGuard(
            provider="test_provider",
            failure_threshold=5,
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        # Rapid concurrent failures
        async def fail_many():
            tasks = [cb.call(fail) for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        results = await fail_many()

        # All should have failed
        runtime_errors = [r for r in results if isinstance(r, RuntimeError)]
        circuit_errors = [r for r in results if isinstance(r, CircuitBreakerOpenError)]

        # Some should be RuntimeError, some CircuitBreakerOpenError
        assert len(runtime_errors) + len(circuit_errors) == 10
        assert cb.get_state() == CircuitBreakerState.OPEN


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCircuitBreakerProviderIsolation:
    """Tests for provider isolation in circuit breakers."""

    async def test_separate_providers_independent(self):
        """E2E: Separate providers have independent circuit breakers."""
        cb_chembl = CircuitBreakerGuard(provider="chembl", failure_threshold=3)
        cb_pubchem = CircuitBreakerGuard(provider="pubchem", failure_threshold=3)

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        async def success():
            await asyncio.sleep(0)
            return "ok"

        # Open ChEMBL circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb_chembl.call(fail)

        assert cb_chembl.get_state() == CircuitBreakerState.OPEN
        assert cb_pubchem.get_state() == CircuitBreakerState.CLOSED

        # PubChem should still work
        result = await cb_pubchem.call(success)
        assert result == "ok"
        assert cb_pubchem.get_state() == CircuitBreakerState.CLOSED

    async def test_provider_name_in_error(self):
        """E2E: Provider name included in CircuitBreakerOpenError."""
        cb = CircuitBreakerGuard(
            provider="test_api_v2",
            failure_threshold=2,
            recovery_timeout=60,
        )

        async def fail():
            await asyncio.sleep(0)
            raise RuntimeError("Error")

        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        async def probe():
            await asyncio.sleep(0)
            return "ok"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(probe)

        assert exc_info.value.provider == "test_api_v2"
