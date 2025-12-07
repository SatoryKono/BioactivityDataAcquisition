"""Token bucket rate limiter implementation for HTTP clients."""

from threading import Lock
import time

from bioetl.domain.clients.base.contracts import RateLimiterABC


class TokenBucketRateLimiterImpl(RateLimiterABC):
    """
    Реализация алгоритма Token Bucket.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        self._rate = rate  # tokens per second
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = Lock()

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

    def wait_if_needed(self) -> None:
        """Compatibility method; acquire already enforces waiting."""
        # Simplified check, acquire does the waiting
        pass

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._rate
        if new_tokens > 0:
            self._tokens = min(self._capacity, self._tokens + new_tokens)
            self._last_refill = now
