"""Checkpoint runtime metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL",
    "CHECKPOINT_LOAD_EVENTS_TOTAL",
    "CHECKPOINT_OPERATOR_DURATION_SECONDS",
    "CHECKPOINT_OPERATOR_OPERATIONS_TOTAL",
    "CHECKPOINT_SAVED_AT_SECONDS",
    "CHECKPOINT_SAVE_DURATION_SECONDS",
    "CHECKPOINT_SAVE_EVENTS_TOTAL",
]

CHECKPOINT_COMPATIBILITY_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_compatibility_events_total",
    "Total checkpoint compatibility outcomes observed during resume validation",
    ["pipeline", "disposition"],
)

CHECKPOINT_LOAD_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_load_events_total",
    "Total checkpoint load decisions observed during runtime and composite resume paths",
    ["pipeline", "status"],
)

CHECKPOINT_OPERATOR_OPERATIONS_TOTAL = Counter(
    "bioetl_checkpoint_operator_operations_total",
    "Total checkpoint admin/operator actions by bounded operation and status",
    ["operation", "status"],
)

CHECKPOINT_OPERATOR_DURATION_SECONDS = Histogram(
    "bioetl_checkpoint_operator_duration_seconds",
    "Duration of checkpoint admin/operator actions in seconds",
    ["operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CHECKPOINT_SAVE_EVENTS_TOTAL = Counter(
    "bioetl_checkpoint_save_events_total",
    "Total checkpoint save outcomes observed during runtime and composite persistence paths",
    ["pipeline", "operation", "status"],
)

CHECKPOINT_SAVED_AT_SECONDS = Gauge(
    "bioetl_checkpoint_saved_at_seconds",
    "Unix timestamp of the latest persisted checkpoint per pipeline",
    ["pipeline"],
)

CHECKPOINT_SAVE_DURATION_SECONDS = Histogram(
    "bioetl_checkpoint_save_duration_seconds",
    "Duration of checkpoint save operations in seconds",
    ["pipeline", "operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)
