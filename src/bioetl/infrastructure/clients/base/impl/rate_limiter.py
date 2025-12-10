"""Token bucket rate limiter implementation for HTTP clients."""

from threading import Lock
import time

from bioetl.domain.clients.base.contracts import RateLimiterABC
from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.observability.factories import default_logging_port


class TokenBucketRateLimiterImpl(RateLimiterABC):
    """
    Реализация алгоритма Token Bucket.
    """

    def __init__(
        self, rate: float, capacity: float, *, logger: LoggingPortABC | None = None
    ) -> None:
        self._rate = rate  # tokens per second
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = Lock()
        self._logger = logger or default_logging_port()
        self._logger.info("rate_limiter_initialized", rate=rate, capacity=capacity)

    @property
    def rate(self) -> float:
        """Get the rate limit (tokens per second)."""
        return self._rate

    def acquire(self) -> None:
        """Block until a token is available, then consume it."""
        with self._lock:
            while True:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                # Wait for enough tokens
                time.sleep(1.0 / self._rate)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._rate
        if new_tokens > 0:
            self._tokens = min(self._capacity, self._tokens + new_tokens)
            self._last_refill = now
