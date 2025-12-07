import time
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states indicating request allowance level."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreakerImpl:
    """
    Реализация паттерна Circuit Breaker.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0

    def allow_request(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            now = time.monotonic()
            if now - self._last_failure_time > self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            # Allow one request to test
            return True

        return True

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failures = 0
        elif self._state == CircuitState.CLOSED:
            self._failures = 0

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN

        elif self._state == CircuitState.CLOSED:
            if self._failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
