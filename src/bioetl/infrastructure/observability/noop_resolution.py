"""Helpers for resolving optional observability ports to null objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort, TracingPort


def resolve_optional_observability_ports(
    *,
    tracer: TracingPort | None,
    metrics: MetricsPort | None,
) -> tuple[TracingPort, MetricsPort]:
    """Resolve optional observability ports to stable null-object implementations."""
    resolved_tracer = tracer if tracer is not None else NoOpTracing()
    resolved_metrics = (
        metrics if metrics is not None else NoOpMetrics(warn_on_use=False)
    )
    return resolved_tracer, resolved_metrics
