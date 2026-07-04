"""Helpers for bounded control-plane read observability."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort

__all__ = ["emit_control_plane_read_metrics"]


def emit_control_plane_read_metrics(
    metrics: MetricsPort | None,
    *,
    store: str,
    operation: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Emit one low-cardinality control-plane read counter and latency sample."""
    if metrics is None:
        return
    labels = {
        "store": store,
        "operation": operation,
        "status": status,
    }
    metrics.increment_counter("bioetl_control_plane_reads_total", 1, labels)
    metrics.observe_histogram(
        "bioetl_control_plane_read_duration_seconds",
        max(duration_seconds, 0.0),
        labels,
    )
