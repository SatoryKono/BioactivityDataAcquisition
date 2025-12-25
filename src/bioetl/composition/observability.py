"""Observability bundle for unified dependency injection.

Aggregates logger, tracer, and metrics into a single injectable dependency,
simplifying constructor signatures across the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import structlog

    from bioetl.domain.ports import DQMonitorPort, MetricsPort, TracingPort


@dataclass(frozen=True)
class ObservabilityBundle:
    """Unified observability context for pipeline execution.

    Aggregates logger, tracer, metrics, and data quality monitor into
    a single injectable dependency. This reduces the number of constructor
    parameters and ensures consistent observability configuration across components.

    Attributes:
        logger: Structured logger for the pipeline.
        tracer: Optional distributed tracing port.
        metrics: Optional metrics collection port.
        dq_monitor: Optional data quality anomaly detector.
    """

    logger: structlog.BoundLogger
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    dq_monitor: DQMonitorPort | None = None

    @classmethod
    def create(
        cls,
        logger: structlog.BoundLogger,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> ObservabilityBundle:
        """Factory method for creating observability bundle.

        Args:
            logger: Structured logger instance.
            tracer: Optional tracer port.
            metrics: Optional metrics port.
            dq_monitor: Optional data quality monitor port.

        Returns:
            Configured ObservabilityBundle instance.
        """
        return cls(logger=logger, tracer=tracer, metrics=metrics, dq_monitor=dq_monitor)

    def bind(self, **kwargs: object) -> ObservabilityBundle:
        """Create new bundle with bound logger context.

        Creates a new bundle with additional context bound to the logger.
        Useful for adding request-specific context (e.g., run_id, entity_id).

        Args:
            **kwargs: Key-value pairs to bind to the logger.

        Returns:
            New ObservabilityBundle with bound logger context.
        """
        return ObservabilityBundle(
            logger=self.logger.bind(**kwargs),
            tracer=self.tracer,
            metrics=self.metrics,
            dq_monitor=self.dq_monitor,
        )


__all__ = ["ObservabilityBundle"]
