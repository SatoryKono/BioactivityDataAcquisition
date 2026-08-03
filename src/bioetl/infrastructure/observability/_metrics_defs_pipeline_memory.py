"""Adaptive-memory runtime metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

__all__ = [
    "MEMORY_BATCH_RESIZE_EVENTS_TOTAL",
    "MEMORY_MONITOR_FALLBACK_EVENTS_TOTAL",
    "MEMORY_PRESSURE_EVENTS_TOTAL",
    "MEMORY_PRESSURE_STATE",
]

MEMORY_PRESSURE_EVENTS_TOTAL = Counter(
    "bioetl_memory_pressure_events_total",
    "Total adaptive-memory decisions that observed active pressure",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_BATCH_RESIZE_EVENTS_TOTAL = Counter(
    "bioetl_memory_batch_resize_events_total",
    "Total adaptive-memory decisions that changed batch size",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_MONITOR_FALLBACK_EVENTS_TOTAL = Counter(
    "bioetl_memory_monitor_fallback_events_total",
    "Total adaptive-memory decisions emitted while using fallback monitor modes",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)

MEMORY_PRESSURE_STATE = Gauge(
    "bioetl_memory_pressure_state",
    "Current bounded adaptive-memory pressure state for the latest decision",
    ["pipeline", "stage", "reason", "monitor_mode", "status"],
)
