"""Resilience domain types and value objects.

Implements RULES.md §3.1 - Error handling and retry policies.
Contains pure configuration and logic for retry behavior (no I/O).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# Default retryable HTTP status codes per RULES.md §3.1.3
# 429: Rate Limit, 500: Internal Server Error, 502-504: Gateway errors
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
        multiplier: Delay multiplier per attempt (default: 2.0, results in 1s, 2s, 4s)
        jitter_range: Min/max jitter factor as tuple (default: (0.1, 0.5))
        retryable_statuses: HTTP status codes to retry (default: 429, 500, 502, 503, 504)
        retryable_exceptions: Exception types to retry (default: ConnectionError, TimeoutError)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        jitter_seed: Seed for deterministic jitter (default: None)

    Example:
        >>> config = RetryConfig(max_attempts=5, multiplier=2.0)
        >>> delay = config.calculate_delay(attempt=0, url="https://api.example.com")
        >>> config.is_retryable_status(429)
        True
    """

    max_attempts: int = 3
    multiplier: float = 2.0
    jitter_range: tuple[float, float] = (0.1, 0.5)
    retryable_statuses: frozenset[int] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_STATUSES
    )
    retryable_exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError)
    base_delay: float = 1.0
    max_delay: float = 60.0
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


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern.

    Implements RULES.md §3.1.4 - Circuit breaker parameters:
    - State machine: CLOSED -> OPEN (after failures) -> HALF_OPEN -> CLOSED
    - Configurable failure threshold
    - Configurable recovery timeout

    Args:
        failure_threshold: Consecutive failures before opening (default: 5)
        recovery_timeout: Seconds to wait in OPEN before testing (default: 300 = 5 minutes)

    Example:
        >>> config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
        >>> config.failure_threshold
        3
    """

    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes


# Backward compatibility alias
RetryPolicy = RetryConfig


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    """Configuration for data source adapters.

    Consolidates adapter-specific settings that were previously hardcoded.
    Single source of truth for batch sizes, timeouts, and page sizes.

    Implements RULES.md §12.1.2 - YAML MUST map to Pydantic and be validated.
    All values are loaded from configs/sources/{provider}.yaml.

    Args:
        batch_size: Number of records per request batch for filtered queries.
            Used when fetching with ID filters (e.g., ChEMBL filter_batch_size).
            Default: 20 (matches ChEMBL config).
        page_size: Number of records per paginated API request.
            Used for standard pagination (e.g., ChEMBL batch_size parameter).
            Default: 1000 (matches ChEMBL config).
        timeout_sec: Request timeout in seconds. Default: 30.0.
        max_retries: Maximum retry attempts for recoverable errors. Default: 3.

    Example:
        >>> config = AdapterConfig(batch_size=50, page_size=500)
        >>> config.batch_size
        50
    """

    batch_size: int = 20
    page_size: int = 1000
    timeout_sec: float = 30.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate configuration values on creation."""
        _validate_positive("batch_size", self.batch_size)
        _validate_positive("page_size", self.page_size)
        _validate_positive("timeout_sec", self.timeout_sec)
        _validate_non_negative("max_retries", self.max_retries)


def _validate_positive(name: str, value: int | float) -> None:
    """Validate that value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _validate_non_negative(name: str, value: int) -> None:
    """Validate that value is non-negative (>= 0)."""
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")
