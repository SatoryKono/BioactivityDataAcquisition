"""Pure helpers for canonical observability metric naming."""

from __future__ import annotations

__all__ = [
    "CANONICAL_OBSERVABILITY_METRIC_PREFIX",
    "canonicalize_observability_metric_name",
    "is_legacy_observability_metric_name",
]

CANONICAL_OBSERVABILITY_METRIC_PREFIX = "bioetl_"


def canonicalize_observability_metric_name(name: str) -> str:
    """Return the canonical Prometheus metric name for one observability signal."""
    normalized = name.strip()
    if not normalized:
        return normalized
    if normalized.startswith(CANONICAL_OBSERVABILITY_METRIC_PREFIX):
        return normalized
    return f"{CANONICAL_OBSERVABILITY_METRIC_PREFIX}{normalized}"


def is_legacy_observability_metric_name(name: str) -> bool:
    """Return whether a metric name still uses the pre-canonical short form."""
    normalized = name.strip()
    return bool(normalized) and not normalized.startswith(
        CANONICAL_OBSERVABILITY_METRIC_PREFIX
    )
