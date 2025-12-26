"""Resilience domain types and value objects.

Implements RULES.md §3.1 - Error handling and retry policies.
Contains pure configuration and logic for retry behavior (no I/O).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for exponential backoff retry strategy.

    Implements RULES.md §4.1 recoverable error handling:
    - Exponential backoff with configurable multiplier
    - Maximum delay cap
    - Deterministic jitter for reproducibility (ADR-014)

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        multiplier: Delay multiplier per attempt (default: 2.0)
        jitter: Random jitter factor 0-1 (default: 0.1)
        deterministic: Use hash-based jitter for reproducibility (default: True)
        jitter_seed: Seed for deterministic jitter (default: None)

    Example:
        >>> policy = RetryPolicy(max_attempts=5, base_delay=2.0)
        >>> delay = policy.calculate_delay(attempt=0, url="https://api.example.com")
        >>> print(f"First retry after {delay:.2f} seconds")
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: float = 0.1
    deterministic: bool = True
    jitter_seed: int | None = None

    def calculate_delay(self, attempt: int, url: str = "") -> float:
        """Calculate delay for given attempt number (0-indexed).

        Uses exponential backoff with optional jitter.
        When deterministic=True, jitter is calculated using MD5 hash
        for cross-process reproducibility (ADR-014).

        Args:
            attempt: Attempt number (0-indexed)
            url: Request URL for deterministic jitter calculation

        Returns:
            Delay in seconds (never negative)
        """
        delay = self.base_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)

        jitter_range = delay * self.jitter
        if self.deterministic:
            # MD5-based deterministic jitter for cross-process reproducibility (ADR-014)
            # Note: hash() is not stable across Python processes due to PYTHONHASHSEED
            hash_input = f"{attempt}:{url}:{self.jitter_seed or 0}"
            digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
            jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF
            # Map 0.0-1.0 to -1.0 to +1.0
            delay += jitter_range * (jitter_factor * 2 - 1)
        else:
            # Non-deterministic jitter (deprecated, use deterministic=True)
            import random
            import warnings

            warnings.warn(
                "Non-deterministic jitter is deprecated per ADR-014. "
                "Use deterministic=True for reproducibility.",
                DeprecationWarning,
                stacklevel=3,
            )
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)

    def is_last_attempt(self, attempt: int) -> bool:
        """Check if this is the last allowed attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            True if no more attempts allowed after this one
        """
        return attempt >= self.max_attempts - 1


# Pre-configured policies for common scenarios
DEFAULT_RETRY_POLICY = RetryPolicy()
"""Default retry policy: 3 attempts, 1s base delay, 2x multiplier."""

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    multiplier=1.5,
)
"""Aggressive retry policy for critical operations: 5 attempts, faster backoff."""

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=2.0,
    max_delay=120.0,
    multiplier=3.0,
)
"""Conservative retry policy for rate-limited APIs: longer delays."""
