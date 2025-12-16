"""Unit tests for CircuitBreaker."""

from __future__ import annotations

import asyncio

import pytest

from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker fault tolerance."""

    @pytest.mark.unit
    def test_initial_state_closed(self) -> None:
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker(provider="test")
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_keeps_closed(self) -> None:
        """Successful calls should keep circuit CLOSED."""
        cb = CircuitBreaker(provider="test", failure_threshold=3)

        async def success() -> str:
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failures_open_circuit(self) -> None:
        """Consecutive failures should open circuit."""
        cb = CircuitBreaker(provider="test", failure_threshold=3)

        async def fail() -> None:
            msg = "error"
            raise RuntimeError(msg)

        # Fail 3 times to trigger opening
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(self) -> None:
        """Open circuit should block subsequent calls."""
        cb = CircuitBreaker(provider="test", failure_threshold=2, recovery_timeout=10)

        async def fail() -> None:
            msg = "error"
            raise RuntimeError(msg)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Next call should be blocked
        async def would_succeed() -> str:
            return "ok"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(would_succeed)

        assert exc_info.value.provider == "test"
        assert exc_info.value.retry_after > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self) -> None:
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,  # Immediate recovery for testing
        )

        async def fail() -> None:
            msg = "error"
            raise RuntimeError(msg)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Wait for recovery (0 seconds in test)
        await asyncio.sleep(0.01)

        # Next call should be allowed (probe request)
        async def success() -> str:
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self) -> None:
        """Failed probe request in HALF_OPEN should reopen circuit."""
        cb = CircuitBreaker(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,  # Immediate recovery for testing
        )

        call_count = 0

        async def fail_always() -> None:
            nonlocal call_count
            call_count += 1
            msg = "error"
            raise RuntimeError(msg)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_always)

        assert cb.get_state() == CircuitBreakerState.OPEN
        initial_trips = cb.get_trips_total()

        # Wait for recovery
        await asyncio.sleep(0.01)

        # Probe request should fail and reopen
        with pytest.raises(RuntimeError):
            await cb.call(fail_always)

        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == initial_trips + 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        """Successful call should reset consecutive failure count."""
        cb = CircuitBreaker(provider="test", failure_threshold=3)

        async def fail() -> None:
            msg = "error"
            raise RuntimeError(msg)

        async def success() -> str:
            return "ok"

        # Fail twice (below threshold)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.CLOSED

        # Success should reset count
        await cb.call(success)

        # Another 2 failures should not open (count was reset)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    def test_manual_reset(self) -> None:
        """Manual reset should restore CLOSED state."""
        cb = CircuitBreaker(provider="test")
        cb.force_open()
        assert cb.get_state() == CircuitBreakerState.OPEN

        cb.reset()
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    def test_force_open(self) -> None:
        """force_open should open circuit and increment trips."""
        cb = CircuitBreaker(provider="test")
        assert cb.get_trips_total() == 0

        cb.force_open()
        assert cb.get_state() == CircuitBreakerState.OPEN
        assert cb.get_trips_total() == 1
