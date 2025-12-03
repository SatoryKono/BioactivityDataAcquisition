"""
Tests for CircuitBreaker implementation.
"""
import time

from bioetl.infrastructure.clients.base.impl.circuit_breaker import (
    CircuitBreakerImpl,
    CircuitState
)


def test_circuit_breaker_flow():
    """Test normal circuit breaker state transitions."""
    cb = CircuitBreakerImpl(failure_threshold=2, recovery_timeout=0.1)

    # Closed state
    assert cb.allow_request()
    cb.record_success()
    # pylint: disable=protected-access
    assert cb._state == CircuitState.CLOSED

    # Failures
    cb.record_failure()
    assert cb._state == CircuitState.CLOSED
    cb.record_failure()
    assert cb._state == CircuitState.OPEN

    # Open state blocks
    assert not cb.allow_request()

    # Wait for recovery
    time.sleep(0.15)
    # Half-open transition check inside allow_request
    assert cb.allow_request()
    assert cb._state == CircuitState.HALF_OPEN

    # Success recovers
    cb.record_success()
    assert cb._state == CircuitState.CLOSED


def test_circuit_breaker_half_open_fail():
    """Test failure in half-open state immediately opens circuit."""
    cb = CircuitBreakerImpl(failure_threshold=1, recovery_timeout=0.0)
    cb.record_failure()
    # pylint: disable=protected-access
    assert cb._state == CircuitState.OPEN

    cb.allow_request()  # To half-open
    assert cb._state == CircuitState.HALF_OPEN

    cb.record_failure()
    assert cb._state == CircuitState.OPEN


def test_circuit_breaker_half_open_allow_request():
    """Test allow_request logic when already in HALF_OPEN state."""
    cb = CircuitBreakerImpl(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    # pylint: disable=protected-access
    assert cb._state == CircuitState.OPEN

    time.sleep(0.15)
    # First call transitions to HALF_OPEN
    assert cb.allow_request() is True
    assert cb._state == CircuitState.HALF_OPEN

    # Second call while HALF_OPEN
    assert cb.allow_request() is True


def test_circuit_breaker_unknown_state():
    """Test allow_request with unknown state (coverage fallback)."""
    cb = CircuitBreakerImpl()
    # Force unknown state
    # pylint: disable=protected-access
    cb._state = "UNKNOWN"
    assert cb.allow_request() is True
