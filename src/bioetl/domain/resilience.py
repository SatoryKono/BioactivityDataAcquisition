"""Pure resilience configuration and retry value objects (RULES.md §3.1)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from bioetl.domain.adapter_config import AdapterConfig
from bioetl.domain.resilience_circuit_breaker import CircuitBreakerConfig

__all__ = [
    "AdapterConfig",
    "CircuitBreakerConfig",
    "RetryConfig",
]


# Default retryable HTTP statuses per RULES.md §3.1.3.
DEFAULT_RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Unified configuration for retry strategy.

    Implements RULES.md §3.1.3 - Retry policy parameters:
    - Exponential backoff with configurable multiplier
    - Maximum delay cap
    - Deterministic jitter for reproducibility (ADR-014)
    - Configurable retryable HTTP status codes
    - Configurable retryable exception types

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        retry_budget_per_request: Optional cap for number of retries per request.
            When set, effective retries = min(retry_budget_per_request, max_attempts - 1).
        multiplier: Delay multiplier per attempt (default: 2.0, results in 1s, 2s, 4s)
        jitter_range: Min/max jitter factor as tuple (default: (0.1, 0.5))
        retryable_statuses: HTTP status codes to retry (default: 429, 500, 502, 503, 504)
        retryable_exceptions: Exception types to retry (default: ConnectionError, TimeoutError)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        max_retry_after_seconds: Optional cap for Retry-After delays. When not set,
            max_delay is used as upper bound.
        jitter_seed: Seed for deterministic jitter (default: None)

    Example:
        >>> config = RetryConfig(max_attempts=5, multiplier=2.0)
        >>> delay = config.calculate_delay(attempt=0, url="https://api.example.com")
        >>> config.is_retryable_status(429)
        True
    """

    max_attempts: int = 3
    retry_budget_per_request: int | None = None
    multiplier: float = 2.0
    jitter_range: tuple[float, float] = (0.1, 0.5)
    retryable_statuses: frozenset[int] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_STATUSES
    )
    retryable_exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError)
    base_delay: float = 1.0
    max_delay: float = 60.0
    max_retry_after_seconds: float | None = None
    jitter_seed: int | None = None

    def is_retryable_status(self, status_code: int) -> bool:
        """Check if HTTP status code is retryable.

        Args:
            status_code: HTTP status code to check

        Returns:
            True if status code should trigger a retry
        """
        return status_code in self.retryable_statuses

    def is_retryable_exception(self, exc: Exception) -> bool:
        """Check if exception is retryable.

        Args:
            exc: Exception to check

        Returns:
            True if exception type should trigger a retry
        """
        return isinstance(exc, self.retryable_exceptions)

    def calculate_delay(self, attempt: int, url: str = "") -> float:
        """Calculate delay for given attempt number (0-indexed).

        Uses exponential backoff with deterministic jitter.
        Jitter is calculated using MD5 hash for cross-process
        reproducibility (ADR-014).

        Args:
            attempt: Attempt number (0-indexed)
            url: Request URL for deterministic jitter calculation

        Returns:
            Delay in seconds (never negative)
        """
        delay = self.base_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)

        # Calculate jitter using range (min, max)
        jitter_min, jitter_max = self.jitter_range
        jitter_span = jitter_max - jitter_min

        # MD5-based deterministic jitter for cross-process reproducibility (ADR-014)
        # Note: hash() is not stable across Python processes due to PYTHONHASHSEED
        hash_input = f"{attempt}:{url}:{self.jitter_seed or 0}"
        digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF

        # Apply jitter: delay * (1 + jitter_amount) where jitter_amount is in [jitter_min, jitter_max]
        jitter_amount = jitter_min + (jitter_span * jitter_factor)
        delay = delay * (1 + jitter_amount)

        return max(0.0, min(delay, self.max_delay))

    def is_last_attempt(self, attempt: int) -> bool:
        """Check if this is the last allowed attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            True if no more attempts allowed after this one
        """
        return attempt >= self.max_attempts - 1

    def effective_retry_budget(self) -> int:
        """Get effective retry budget (number of retries, not attempts).

        Returns:
            Number of retries allowed, capped by retry_budget_per_request if set.
        """
        max_retries = max(0, self.max_attempts - 1)
        if self.retry_budget_per_request is None:
            return max_retries
        return max(0, min(self.retry_budget_per_request, max_retries))

    def clamp_retry_after(self, retry_after_seconds: float) -> float:
        """Clamp Retry-After delay to configured upper bound.

        Args:
            retry_after_seconds: Delay in seconds suggested by the provider's Retry-After header.

        Returns:
            Clamped delay in seconds, between 0.0 and the configured upper bound.
        """
        upper_bound = (
            self.max_retry_after_seconds
            if self.max_retry_after_seconds is not None
            else self.max_delay
        )
        return max(0.0, min(retry_after_seconds, upper_bound))


# Keep AdapterConfig importable from resilience for stable public API.
