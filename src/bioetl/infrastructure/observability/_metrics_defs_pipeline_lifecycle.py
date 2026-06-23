"""Pipeline lifecycle and shutdown Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

__all__ = [
    "OBSERVABILITY_EVENTS_TOTAL",
    "PHASE_DURATION_SECONDS",
    "PIPELINE_RUNS_TOTAL",
    "POSTRUN_PHASE_DURATION_SECONDS",
    "POSTRUN_PHASE_EVENTS_TOTAL",
    "SHUTDOWN_COMPLETED",
    "SHUTDOWN_INITIATED",
    "STORAGE_OPTIMIZATION_TOTAL",
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

POSTRUN_PHASE_EVENTS_TOTAL = Counter(
    "bioetl_postrun_phase_events_total",
    "Total bounded postrun phase outcomes by pipeline, phase, and status",
    ["pipeline", "phase", "status"],
)

POSTRUN_PHASE_DURATION_SECONDS = Histogram(
    "bioetl_postrun_phase_duration_seconds",
    "Duration of postrun subphases in seconds",
    ["pipeline", "phase", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)

OBSERVABILITY_EVENTS_TOTAL = Counter(
    "bioetl_observability_events_total",
    "Unified observability events emitted by pipeline observer",
    ["event", "provider", "pipeline", "severity", "error_type"],
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
