"""Metrics collector convenience wrapper."""

from __future__ import annotations

from bioetl.infrastructure.observability.metrics_definitions import (
    ERRORS_TOTAL,
    RECORDS_PROCESSED_TOTAL,
)


class MetricsCollector:
    """Collector for pipeline metrics.

    Wraps Prometheus metrics with pipeline context.
    """

    # Any: optional Prometheus CollectorRegistry has no strict protocol in domain
    def __init__(
        self,
        pipeline_name: str,
        registry: object = None,
    ) -> None:
        """Initialize the metrics collector.

        Args:
            pipeline_name: Name of the pipeline.
            registry: Optional Prometheus registry (unused as metrics are global).

        """
        self.pipeline_name = pipeline_name
        self.registry = registry

    def record_processed(
        self,
        layer: str,
        count: int = 1,
        run_type: str = "incremental",
    ) -> None:
        """Record processed records count.

        Args:
            layer: Pipeline stage label (e.g., "bronze", "silver", "gold").
            count: Number of records processed (default: 1).
            run_type: Type of run for metric labelling (default: "incremental").

        """
        RECORDS_PROCESSED_TOTAL.labels(
            pipeline=self.pipeline_name,
            stage=layer,
            run_type=run_type,
        ).inc(count)

    def record_error(self, error_code: str, stage: str = "processing") -> None:
        """Record an error occurrence.

        Args:
            error_code: Categorised error code identifying the failure type.
            stage: Pipeline stage where the error occurred (default: "processing").

        """
        ERRORS_TOTAL.labels(
            pipeline=self.pipeline_name,
            stage=stage,
            error_code=error_code,
        ).inc()


__all__ = ["MetricsCollector"]
