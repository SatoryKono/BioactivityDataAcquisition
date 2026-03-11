"""Shared latency policy for adapter health probes."""

from __future__ import annotations

DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS = 5.0

__all__ = [
    "DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS",
    "is_slow_health_probe",
]


def is_slow_health_probe(
    *,
    elapsed_seconds: float,
    slow_threshold_seconds: float = DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
) -> bool:
    """Return whether a health probe should be treated as slow/degraded."""
    return elapsed_seconds > slow_threshold_seconds
