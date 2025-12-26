"""Token bucket rate limiter for HTTP requests.

Implements RULES.md Section 5.1 rate limiting requirements.
Uses asyncio for non-blocking token acquisition.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


@dataclass
class TokenBucket:
    """Async token bucket rate limiter.

    Implements the token bucket algorithm for rate limiting API requests.
    Tokens are replenished at a fixed rate up to a maximum capacity.

    Args:
        rate: Tokens added per second
        capacity: Maximum tokens in bucket

    Example:
        >>> bucket = TokenBucket(rate=5.0, capacity=10)  # 5 req/sec, burst of 10
        >>> await bucket.acquire()  # Wait for token
        >>> await bucket.acquire(tokens=2)  # Acquire multiple tokens

    Provider rate limits (from RULES.md Appendix A):
        - PubChem: 5 req/sec
        - UniProt: 100 req/sec (with API key)
        - OpenAlex: 10 req/sec (polite)
        - Crossref: 50 req/sec (polite)
        - Semantic Scholar: 100 req/5min = ~0.33 req/sec
        - PubMed: 3 req/sec (10 with API key)

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

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Raises:
            ValueError: If tokens > capacity

        """
        if tokens > self.capacity:
            msg = f"Cannot acquire {tokens} tokens, capacity is {self.capacity}"
            raise ValueError(msg)

        total_wait_time = 0.0
        async with self._lock:
            while True:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    self._record_metrics(total_wait_time)
                    return

                # Calculate wait time for needed tokens
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
        """Return current available tokens (floor of float value)."""
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


# Pre-configured buckets for known providers
def create_pubchem_bucket(
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for PubChem (5 req/sec).

    Args:
        metrics: Optional metrics port for observability

    """
    return TokenBucket(rate=5.0, capacity=5, provider="pubchem", metrics=metrics)


def create_uniprot_bucket(
    with_api_key: bool = False,
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for UniProt.

    Args:
        with_api_key: True if using API key (100 req/sec vs default)
        metrics: Optional metrics port for observability

    """
    rate = 100.0 if with_api_key else 10.0
    return TokenBucket(rate=rate, capacity=int(rate), provider="uniprot", metrics=metrics)


def create_openalex_bucket(
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for OpenAlex (10 req/sec polite).

    Args:
        metrics: Optional metrics port for observability

    """
    return TokenBucket(rate=10.0, capacity=10, provider="openalex", metrics=metrics)


def create_crossref_bucket(
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for Crossref (50 req/sec polite).

    Args:
        metrics: Optional metrics port for observability

    """
    return TokenBucket(rate=50.0, capacity=50, provider="crossref", metrics=metrics)


def create_semantic_scholar_bucket(
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for Semantic Scholar (100 req/5min).

    Args:
        metrics: Optional metrics port for observability

    """
    # 100 requests per 5 minutes = 0.333 req/sec
    return TokenBucket(rate=0.333, capacity=10, provider="semantic_scholar", metrics=metrics)


def create_pubmed_bucket(
    with_api_key: bool = False,
    metrics: MetricsPort | None = None,
) -> TokenBucket:
    """Create rate limiter for PubMed.

    Args:
        with_api_key: True if using API key (10 req/sec vs 3 req/sec)
        metrics: Optional metrics port for observability

    """
    rate = 10.0 if with_api_key else 3.0
    return TokenBucket(rate=rate, capacity=int(rate), provider="pubmed", metrics=metrics)
