"""Unit tests for shared circuit breaker contract semantics."""

from __future__ import annotations

import pytest

from bioetl.domain.types import CircuitBreakerState
from bioetl.infrastructure.adapters._circuit_breaker_contract import (
    CircuitBreakerSnapshot,
    CircuitBreakerTransitionEvent,
    evaluate_attempt,
    on_failure_transition,
    on_success_transition,
    retry_after_seconds,
)


pytestmark = pytest.mark.unit

class TestCircuitBreakerContract:
    """State transition tests shared by both breaker implementations."""

    def test_open_state_blocks_before_recovery_timeout(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            recovery_timeout=10.0,
            last_failure_time=95.0,
        )

        decision = evaluate_attempt(snapshot, now=100.0)

        assert decision.allow_request is False
        assert decision.next_state == CircuitBreakerState.OPEN
        assert decision.event == CircuitBreakerTransitionEvent.NONE
        assert decision.retry_after == pytest.approx(5.0)

    def test_open_state_allows_probe_after_recovery_timeout(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            recovery_timeout=10.0,
            last_failure_time=80.0,
        )

        decision = evaluate_attempt(snapshot, now=100.0)

        assert decision.allow_request is True
        assert decision.next_state == CircuitBreakerState.HALF_OPEN
        assert decision.event == CircuitBreakerTransitionEvent.HALF_OPENED
        assert decision.retry_after == pytest.approx(0.0)

    def test_open_state_without_failure_timestamp_stays_blocked(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.OPEN,
            failure_count=3,
            recovery_timeout=60.0,
            last_failure_time=None,
        )

        decision = evaluate_attempt(snapshot, now=100.0)

        assert decision.allow_request is False
        assert decision.retry_after == pytest.approx(60.0)

    def test_success_from_half_open_closes_breaker(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.HALF_OPEN,
            failure_count=2,
            recovery_timeout=10.0,
        )

        transition = on_success_transition(snapshot)

        assert transition.next_state == CircuitBreakerState.CLOSED
        assert transition.failure_count == 0
        assert transition.event == CircuitBreakerTransitionEvent.CLOSED

    def test_failure_threshold_opens_closed_breaker(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.CLOSED,
            failure_count=2,
            recovery_timeout=10.0,
        )

        transition = on_failure_transition(snapshot, failure_threshold=3)

        assert transition.next_state == CircuitBreakerState.OPEN
        assert transition.failure_count == 3
        assert transition.trips_delta == 1
        assert transition.event == CircuitBreakerTransitionEvent.OPENED

    def test_half_open_failure_reopens_breaker(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.HALF_OPEN,
            failure_count=2,
            recovery_timeout=10.0,
        )

        transition = on_failure_transition(snapshot, failure_threshold=5)

        assert transition.next_state == CircuitBreakerState.OPEN
        assert transition.failure_count == 3
        assert transition.trips_delta == 1

    def test_retry_after_for_non_open_state_is_zero(self) -> None:
        snapshot = CircuitBreakerSnapshot(
            state=CircuitBreakerState.CLOSED,
            failure_count=0,
            recovery_timeout=10.0,
        )

        assert retry_after_seconds(snapshot, now=100.0) == pytest.approx(0.0)
