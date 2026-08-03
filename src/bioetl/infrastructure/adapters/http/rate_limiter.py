"""Token bucket rate limiter for HTTP requests.

Implements RULES.md Section 5.1 rate limiting requirements.
Uses asyncio for non-blocking token acquisition.
"""

from __future__ import annotations

__all__ = ["TokenBucketRateLimiter"]


import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


@dataclass
class TokenBucketRateLimiter:
    """Async token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting API requests.
    Tokens are replenished at a fixed rate up to a maximum capacity.

    Args:
        rate: Tokens added per second
        capacity: Maximum tokens in bucket

    Example:
        >>> bucket = TokenBucketRateLimiter(rate=5.0, capacity=10)  # 5 req/sec, burst of 10
        >>> await bucket.acquire()  # Wait for token
        >>> await bucket.acquire(tokens=2)  # Acquire multiple tokens

    Provider rate limits (configurable via source YAML):
        - PubChem: 5 req/sec
        - UniProt: fair-use throttling (configurable)
        - OpenAlex: 10 req/sec (polite pool, with mailto)
        - Crossref: 50 req/sec (polite pool, with mailto)
        - Semantic Scholar: 1 req/sec (no key) / 10 req/sec (with API key)
        - PubMed: 3 req/sec (10 with API key via NCBI E-utilities)

    """

    rate: float
    capacity: int
    provider: str = "unknown"
    metrics: MetricsPort | None = None
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        """Initialize bucket with full capacity."""
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * self.rate
        self._tokens = min(self.capacity, self._tokens + tokens_to_add)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Releases the lock before sleeping so other coroutines can
        check/acquire tokens concurrently.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Raises:
            ValueError: If tokens > capacity

        """
        if tokens > self.capacity:
            msg = f"Cannot acquire {tokens} tokens, capacity is {self.capacity}"
            raise ValueError(msg)

        total_wait_time = 0.0
        while True:
            async with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._record_metrics(total_wait_time)
                    return

                # Calculate wait time — lock is released before sleep
                deficit = tokens - self._tokens
                wait_time = deficit / self.rate

            total_wait_time += wait_time
            await asyncio.sleep(wait_time)

    def _record_metrics(self, wait_time: float) -> None:
        """Record rate limiter metrics.

        Args:
            wait_time: Total time spent waiting for tokens (seconds)

        """
        if self.metrics is None:
            return

        labels = {"provider": self.provider}

        self.metrics.set_gauge(
            "bioetl_rate_limiter_tokens_available",
            self._tokens,
            labels,
        )

        self.metrics.observe_histogram(
            "bioetl_rate_limiter_wait_seconds",
            wait_time,
            labels,
        )

    def available_tokens(self) -> int:
        """Return current available tokens (floor of float value).

        Returns:
            Computed integer value.
        """
        self._refill()
        return int(self._tokens)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if acquired, False otherwise

        """
        self._refill()

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False
