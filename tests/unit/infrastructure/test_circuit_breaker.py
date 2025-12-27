"""Unit tests for CircuitBreaker."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters.http.circuit_breaker import (
    METRIC_CIRCUIT_BREAKER_STATE,
    METRIC_CIRCUIT_BREAKER_TRIPS,
    CircuitBreaker,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker fault tolerance."""

    @pytest.mark.unit
    def test_initial_state_closed(self) -> None:
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker(provider="test")
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_success_keeps_closed(self) -> None:
        """Successful calls should keep circuit CLOSED."""
        cb = CircuitBreaker(provider="test", failure_threshold=3)

        async def success() -> str:
            return "ok"

        result = await cb.call(success)
        assert result == "ok"
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
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


class TestCircuitBreakerMetrics:
    """Tests for CircuitBreaker metrics emission."""

    @pytest.fixture
    def mock_metrics(self) -> MagicMock:
        """Create a mock MetricsPort."""
        return MagicMock(spec=MetricsPort)

    @pytest.mark.unit
    def test_initial_state_emits_closed_metric(self, mock_metrics: MagicMock) -> None:
        """Circuit breaker should emit CLOSED state metric on initialization."""
        CircuitBreaker(provider="test", metrics=mock_metrics)

        mock_metrics.set_gauge.assert_called_once_with(
            METRIC_CIRCUIT_BREAKER_STATE,
            0.0,  # CLOSED = 0
            {"provider": "test"},
        )

    @pytest.mark.unit
    async def test_closed_to_open_emits_state_and_trip_metrics(
        self, mock_metrics: MagicMock
    ) -> None:
        """CLOSED -> OPEN transition should emit state and trip metrics."""
        cb = CircuitBreaker(provider="test", failure_threshold=3, metrics=mock_metrics)

        async def fail() -> None:
            raise RuntimeError("error")

        # Trigger 3 failures to open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Check state gauge was set to OPEN (2.0)
        mock_metrics.set_gauge.assert_called_with(
            METRIC_CIRCUIT_BREAKER_STATE,
            2.0,  # OPEN = 2
            {"provider": "test"},
        )

        # Check trip counter was incremented
        mock_metrics.increment_counter.assert_called_once_with(
            METRIC_CIRCUIT_BREAKER_TRIPS,
            1,
            {"provider": "test"},
        )

    @pytest.mark.unit
    async def test_open_to_half_open_emits_metric(
        self, mock_metrics: MagicMock
    ) -> None:
        """OPEN -> HALF_OPEN transition should emit state metric."""
        cb = CircuitBreaker(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
            metrics=mock_metrics,
        )

        async def fail() -> None:
            raise RuntimeError("error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN
        mock_metrics.reset_mock()

        # Wait for recovery
        await asyncio.sleep(0.01)

        # Probe request that triggers HALF_OPEN transition
        async def success() -> str:
            return "ok"

        await cb.call(success)

        # Should have called set_gauge twice: once for HALF_OPEN, once for CLOSED
        calls = mock_metrics.set_gauge.call_args_list
        assert len(calls) >= 2

        # First call should be HALF_OPEN (1.0)
        assert calls[0][0] == (
            METRIC_CIRCUIT_BREAKER_STATE,
            1.0,  # HALF_OPEN = 1
            {"provider": "test"},
        )

        # Second call should be CLOSED (0.0)
        assert calls[1][0] == (
            METRIC_CIRCUIT_BREAKER_STATE,
            0.0,  # CLOSED = 0
            {"provider": "test"},
        )

    @pytest.mark.unit
    async def test_half_open_failure_emits_metrics(
        self, mock_metrics: MagicMock
    ) -> None:
        """Failed probe in HALF_OPEN should emit state and trip metrics."""
        cb = CircuitBreaker(
            provider="test",
            failure_threshold=2,
            recovery_timeout=0,
            metrics=mock_metrics,
        )

        async def fail() -> None:
            raise RuntimeError("error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN
        mock_metrics.reset_mock()

        # Wait for recovery
        await asyncio.sleep(0.01)

        # Failed probe request
        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Should have emitted HALF_OPEN then OPEN state
        gauge_calls = mock_metrics.set_gauge.call_args_list
        assert len(gauge_calls) >= 2

        # First should be HALF_OPEN
        assert gauge_calls[0][0][1] == 1.0  # HALF_OPEN

        # Second should be OPEN
        assert gauge_calls[1][0][1] == 2.0  # OPEN

        # Should have incremented trip counter
        mock_metrics.increment_counter.assert_called_with(
            METRIC_CIRCUIT_BREAKER_TRIPS,
            1,
            {"provider": "test"},
        )

    @pytest.mark.unit
    def test_force_open_emits_metrics(self, mock_metrics: MagicMock) -> None:
        """force_open should emit state and trip metrics."""
        cb = CircuitBreaker(provider="test", metrics=mock_metrics)
        mock_metrics.reset_mock()

        cb.force_open()

        mock_metrics.set_gauge.assert_called_with(
            METRIC_CIRCUIT_BREAKER_STATE,
            2.0,  # OPEN = 2
            {"provider": "test"},
        )
        mock_metrics.increment_counter.assert_called_once_with(
            METRIC_CIRCUIT_BREAKER_TRIPS,
            1,
            {"provider": "test"},
        )

    @pytest.mark.unit
    def test_reset_emits_closed_metric(self, mock_metrics: MagicMock) -> None:
        """reset should emit CLOSED state metric."""
        cb = CircuitBreaker(provider="test", metrics=mock_metrics)
        cb.force_open()
        mock_metrics.reset_mock()

        cb.reset()

        mock_metrics.set_gauge.assert_called_with(
            METRIC_CIRCUIT_BREAKER_STATE,
            0.0,  # CLOSED = 0
            {"provider": "test"},
        )

    @pytest.mark.unit
    def test_no_metrics_when_none_provided(self) -> None:
        """Circuit breaker should work without metrics (None)."""
        cb = CircuitBreaker(provider="test", metrics=None)

        # Should not raise any errors
        cb.force_open()
        cb.reset()
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.unit
    async def test_failures_below_threshold_no_trip_metric(
        self, mock_metrics: MagicMock
    ) -> None:
        """Failures below threshold should not emit trip metrics."""
        cb = CircuitBreaker(provider="test", failure_threshold=3, metrics=mock_metrics)

        async def fail() -> None:
            raise RuntimeError("error")

        # Fail 2 times (below threshold of 3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitBreakerState.CLOSED
        mock_metrics.increment_counter.assert_not_called()
