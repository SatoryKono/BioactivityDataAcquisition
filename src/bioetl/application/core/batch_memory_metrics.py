"""Adaptive batch memory metrics helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.batch_memory_decision_policy import decision_status

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

_MEMORY_PRESSURE_EVENTS_METRIC = "bioetl_memory_pressure_events_total"
_MEMORY_BATCH_RESIZE_EVENTS_METRIC = "bioetl_memory_batch_resize_events_total"
_MEMORY_MONITOR_FALLBACK_EVENTS_METRIC = "bioetl_memory_monitor_fallback_events_total"
_MEMORY_PRESSURE_STATE_METRIC = "bioetl_memory_pressure_state"
_ALLOWED_MONITOR_MODES = frozenset(
    {"psutil", "resource", "estimate", "unknown", "disabled", "config_budget"}
)
_FALLBACK_MONITOR_MODES = frozenset({"resource", "estimate", "unknown"})
_FALLBACK_MONITOR_MODE = "unknown"


def _normalize_monitor_mode(monitor_mode: str) -> str:
    """Constrain monitor_mode labels to the known allowlist."""
    if monitor_mode in _ALLOWED_MONITOR_MODES:
        return monitor_mode
    return _FALLBACK_MONITOR_MODE


def emit_decision_metrics(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str,
    stage: str,
    old_size: int,
    new_size: int,
    pressure_state: bool | None,
    monitor_mode: str,
    reason: str,
) -> None:
    """Emit bounded adaptive-memory metrics for one decision."""
    if metrics is None:
        return
    status = decision_status(
        old_size=old_size,
        new_size=new_size,
        pressure_state=pressure_state,
    )
    normalized_mode = _normalize_monitor_mode(monitor_mode)
    labels = {
        "pipeline": pipeline_name,
        "stage": stage,
        "reason": reason,
        "monitor_mode": normalized_mode,
        "status": status,
    }
    metrics.set_gauge(
        _MEMORY_PRESSURE_STATE_METRIC,
        1.0 if pressure_state is True else 0.0,
        labels,
    )
    if pressure_state is True:
        metrics.increment_counter(
            _MEMORY_PRESSURE_EVENTS_METRIC,
            1,
            labels,
        )
    if old_size != new_size:
        metrics.increment_counter(
            _MEMORY_BATCH_RESIZE_EVENTS_METRIC,
            1,
            labels,
        )
    if normalized_mode in _FALLBACK_MONITOR_MODES:
        metrics.increment_counter(
            _MEMORY_MONITOR_FALLBACK_EVENTS_METRIC,
            1,
            labels,
        )


__all__ = ["emit_decision_metrics"]
