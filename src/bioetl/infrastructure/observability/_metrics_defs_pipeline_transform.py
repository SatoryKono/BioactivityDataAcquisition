"""Pipeline transform and filter Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "FILTER_COMBINATIONS_LOADED_TOTAL",
    "TRANSFORM_DURATION_SECONDS",
    "TRANSFORM_ERRORS_TOTAL",
]

TRANSFORM_DURATION_SECONDS = Histogram(
    "bioetl_transform_duration_seconds",
    "Duration of data transformation in seconds",
    ["provider", "entity_type"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

TRANSFORM_ERRORS_TOTAL = Counter(
    "bioetl_transform_errors_total",
    "Total transformation errors",
    ["provider", "entity_type", "error_type"],
)

FILTER_COMBINATIONS_LOADED_TOTAL = Counter(
    "bioetl_filter_combinations_loaded_total",
    "Total filter combinations loaded from multi-filter source",
    ["pipeline", "source_kind"],
)
