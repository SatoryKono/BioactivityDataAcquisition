"""Runtime write resilience policies for storage adapters.

Defines retry/backoff policy objects used by atomic metadata writes and
Silver Delta merge execution.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY",
    "DEFAULT_ATOMIC_REPLACE_RETRY_POLICY",
    "DEFAULT_SILVER_MERGE_POLICY",
    "NON_WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY",
    "NON_WINDOWS_ATOMIC_REPLACE_RETRY_POLICY",
    "WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY",
    "WINDOWS_ATOMIC_REPLACE_RETRY_POLICY",
    "AdaptiveRetryPolicy",
    "SilverMergeResiliencePolicy",
    "build_default_atomic_group_replace_retry_policy",
    "build_default_atomic_replace_retry_policy",
    "build_default_silver_merge_policy",
]


import os
from collections.abc import Callable
from dataclasses import dataclass

JitterFn = Callable[[float, float], float]


def _is_windows_platform() -> bool:
    """Return True when running on Windows-like platform semantics."""
    return os.name == "nt"


def _deterministic_jitter_seconds(
    retry_count: int,
    max_jitter_seconds: float,
) -> float:
    """Return deterministic jitter value bounded by ``max_jitter_seconds``.

    Uses a small repeating phase cycle to avoid random-dependent behavior
    while still providing bounded per-attempt perturbation.

    Returns:
        Jitter float in seconds, bounded by max_jitter_seconds, or 0.0 if max is non-positive.
    """
    if max_jitter_seconds <= 0.0:
        return 0.0
    phase = (max(0, retry_count) % 4) + 1
    return float((phase / 4.0) * max_jitter_seconds)


@dataclass(frozen=True, slots=True)
class AdaptiveRetryPolicy:
    """Retry policy with optional adaptive backoff and deterministic jitter."""

    enabled: bool
    max_retries: int
    base_delay_seconds: float
    max_delay_seconds: float
    jitter_seconds: float = 0.0
    adaptive: bool = True

    def should_retry(self, retry_count: int) -> bool:
        """Return ``True`` when another retry is allowed.

        Returns:
            True if retries are enabled and retry_count is below max_retries, False otherwise.
        """
        return self.enabled and retry_count < self.max_retries

    def calculate_delay(
        self,
        retry_count: int,
        *,
        jitter_fn: JitterFn | None = None,
    ) -> float:
        """Calculate bounded delay for the given 0-indexed retry number.

        Returns:
            Delay float in seconds, bounded by max_delay_seconds, including optional jitter.
        """
        if self.base_delay_seconds <= 0.0 or self.max_delay_seconds <= 0.0:
            return 0.0

        delay: float
        if self.adaptive:
            delay = self.base_delay_seconds * float(2 ** max(0, retry_count))
        else:
            delay = self.base_delay_seconds * float(max(0, retry_count) + 1)

        bounded_delay = float(min(delay, self.max_delay_seconds))
        if self.jitter_seconds <= 0.0:
            return float(max(0.0, bounded_delay))

        if jitter_fn is not None:
            jitter = float(max(0.0, jitter_fn(0.0, self.jitter_seconds)))
        else:
            jitter = _deterministic_jitter_seconds(
                retry_count=retry_count,
                max_jitter_seconds=self.jitter_seconds,
            )
        return float(max(0.0, min(self.max_delay_seconds, bounded_delay + jitter)))


@dataclass(frozen=True, slots=True)
class SilverMergeResiliencePolicy:
    """Merge timeout/retry policy bundle for Silver Delta writes."""

    execution_timeout_seconds: float
    commit_retry: AdaptiveRetryPolicy
    timeout_retry: AdaptiveRetryPolicy
    plain_write_process_isolation: bool = False


WINDOWS_ATOMIC_REPLACE_RETRY_POLICY = AdaptiveRetryPolicy(
    enabled=True,
    max_retries=20,
    base_delay_seconds=0.01,
    max_delay_seconds=0.25,
    jitter_seconds=0.0,
    adaptive=True,
)

NON_WINDOWS_ATOMIC_REPLACE_RETRY_POLICY = AdaptiveRetryPolicy(
    enabled=True,
    max_retries=3,
    base_delay_seconds=0.002,
    max_delay_seconds=0.05,
    jitter_seconds=0.0,
    adaptive=True,
)

WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY = AdaptiveRetryPolicy(
    enabled=True,
    max_retries=10,
    base_delay_seconds=0.001,
    max_delay_seconds=0.01,
    jitter_seconds=0.0,
    adaptive=True,
)

NON_WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY = AdaptiveRetryPolicy(
    enabled=True,
    max_retries=3,
    base_delay_seconds=0.001,
    max_delay_seconds=0.01,
    jitter_seconds=0.0,
    adaptive=True,
)


def build_default_atomic_replace_retry_policy() -> AdaptiveRetryPolicy:
    """Return OS-specific default policy for atomic Path.replace retries.

    Returns:
        AdaptiveRetryPolicy configured for Windows (20 retries) or non-Windows (3 retries).
    """
    if _is_windows_platform():
        return WINDOWS_ATOMIC_REPLACE_RETRY_POLICY
    return NON_WINDOWS_ATOMIC_REPLACE_RETRY_POLICY


DEFAULT_ATOMIC_REPLACE_RETRY_POLICY = build_default_atomic_replace_retry_policy()


def build_default_atomic_group_replace_retry_policy() -> AdaptiveRetryPolicy:
    """Return a rename-group policy tuned for multi-file commit throughput.

    Group commits may apply the retry backoff many times in one operation.
    Keep the policy resilient to transient sharing violations while using
    a much smaller per-file delay budget than single-file metadata writes.
    """
    if _is_windows_platform():
        return WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY
    return NON_WINDOWS_ATOMIC_GROUP_REPLACE_RETRY_POLICY


DEFAULT_ATOMIC_GROUP_REPLACE_RETRY_POLICY = (
    build_default_atomic_group_replace_retry_policy()
)


def build_default_silver_merge_policy() -> SilverMergeResiliencePolicy:
    """Build default Silver merge policy aligned with PipelineSettings defaults.

    Returns:
        SilverMergeResiliencePolicy with 45s execution timeout, commit retry, and timeout retry.
    """
    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=45.0,
        commit_retry=AdaptiveRetryPolicy(
            enabled=True,
            max_retries=3,
            base_delay_seconds=0.250,
            max_delay_seconds=2.0,
            jitter_seconds=0.050,
            adaptive=True,
        ),
        timeout_retry=AdaptiveRetryPolicy(
            enabled=True,
            max_retries=1,
            base_delay_seconds=0.200,
            max_delay_seconds=2.0,
            jitter_seconds=0.050,
            adaptive=True,
        ),
    )


DEFAULT_SILVER_MERGE_POLICY = build_default_silver_merge_policy()
