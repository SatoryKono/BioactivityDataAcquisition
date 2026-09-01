"""Metrics collector convenience wrapper."""

from __future__ import annotations

from bioetl.domain.ports import MetricsPort


class MetricsCollector:
    """Collector for pipeline metrics.

    Wraps an injected MetricsPort with pipeline context instead of touching
    raw Prometheus collectors directly from this module.
    """

    def __init__(
        self,
        pipeline_name: str,
        metrics: MetricsPort | None = None,
        registry: object = None,
    ) -> None:
        """Initialize the metrics collector.

        Args:
            pipeline_name: Name of the pipeline.
            metrics: Metrics port used for emission. When omitted, uses the
                process-wide PrometheusMetrics adapter.
            registry: Optional Prometheus registry (legacy unused parameter).
        """
        self.pipeline_name = pipeline_name
        if metrics is None:
            from bioetl.infrastructure.observability.prometheus_metrics import (
                PrometheusMetrics,
            )

            metrics = PrometheusMetrics()
        self.metrics: MetricsPort = metrics
        self.registry = registry

    def record_processed(
        self,
        layer: str,
        count: int = 1,
        run_type: str = "incremental",
    ) -> None:
        """Record processed records count."""
        self.metrics.increment_counter(
            "bioetl_records_processed_total",
            count,
            {
                "pipeline": self.pipeline_name,
                "stage": layer,
                "run_type": run_type,
            },
        )

    def record_error(self, error_code: str, stage: str = "processing") -> None:
        """Record an error occurrence."""
        self.metrics.increment_counter(
            "bioetl_errors_total",
            1,
            {
                "pipeline": self.pipeline_name,
                "stage": stage,
                "error_code": error_code,
            },
        )


__all__ = ["MetricsCollector"]
