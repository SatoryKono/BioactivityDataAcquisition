"""Pipeline lifecycle, transform, and shutdown metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "DQ_SOFT_THRESHOLD_EXCEEDED",
    "FILTER_COMBINATIONS_LOADED_TOTAL",
    "OBSERVABILITY_EVENTS_TOTAL",
    "PHASE_DURATION_SECONDS",
    "PIPELINE_RUNS_TOTAL",
    "SHUTDOWN_COMPLETED",
    "SHUTDOWN_INITIATED",
    "STORAGE_OPTIMIZATION_TOTAL",
    "TRANSFORM_DURATION_SECONDS",
    "TRANSFORM_ERRORS_TOTAL",
]

PIPELINE_RUNS_TOTAL = Counter(
    "bioetl_pipeline_runs_total",
    "Total number of pipeline runs",
    ["pipeline", "run_type", "status"],
)

PHASE_DURATION_SECONDS = Histogram(
    "bioetl_phase_duration_seconds",
    "Duration of pipeline lifecycle phases in seconds",
    ["pipeline", "phase", "status"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

OBSERVABILITY_EVENTS_TOTAL = Counter(
    "bioetl_observability_events_total",
    "Unified observability events emitted by pipeline observer",
    ["event", "provider", "pipeline", "severity", "error_type"],
)

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

DQ_SOFT_THRESHOLD_EXCEEDED = Counter(
    "bioetl_dq_soft_threshold_exceeded",
    "Total times DQ soft threshold was exceeded",
    ["pipeline"],
)

SHUTDOWN_INITIATED = Counter(
    "bioetl_shutdown_initiated",
    "Total shutdown initiations",
    ["reason"],
)

SHUTDOWN_COMPLETED = Counter(
    "bioetl_shutdown_completed",
    "Total shutdown completions",
    ["reason"],
)

STORAGE_OPTIMIZATION_TOTAL = Counter(
    "bioetl_storage_optimization_total",
    "Total storage optimization operations",
    ["pipeline", "status"],
)

FILTER_COMBINATIONS_LOADED_TOTAL = Counter(
    "bioetl_filter_combinations_loaded_total",
    "Total filter combinations loaded from multi-filter source",
    ["pipeline", "source_file"],
)
