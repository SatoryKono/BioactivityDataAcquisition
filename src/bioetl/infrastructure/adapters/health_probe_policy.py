"""Shared latency policy for adapter health probes."""

from __future__ import annotations

DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS = 5.0

__all__ = [
    "DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS",
    "is_slow_health_probe",
    "resolve_health_probe_elapsed",
]


def is_slow_health_probe(
    *,
    elapsed_seconds: float,
    slow_threshold_seconds: float = DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
) -> bool:
    """Return whether a health probe should be treated as slow/degraded."""
    return elapsed_seconds > slow_threshold_seconds


def resolve_health_probe_elapsed(response: object, fallback: float) -> float:
    """Prefer measured transport time, excluding admission and retry delays."""
    extensions = getattr(response, "extensions", None)
    if isinstance(extensions, dict):
        transport_seconds = extensions.get("bioetl_transport_seconds")
        if isinstance(transport_seconds, (int, float)):
            return transport_seconds
    return fallback
