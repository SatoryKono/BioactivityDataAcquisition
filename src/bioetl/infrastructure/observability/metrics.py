"""Prometheus Metrics for BioETL."""

from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from prometheus_client import CollectorRegistry

# Generic pipeline metrics
PIPELINE_DURATION_SECONDS = Histogram(
    "pipeline_duration_seconds",
    "Duration of pipeline runs in seconds",
    ["pipeline_name", "run_type", "status"],
)

RECORDS_PROCESSED_TOTAL = Counter(
    "records_processed_total",
    "Total number of records processed by the pipeline",
    ["pipeline_name", "run_type", "layer"],  # bronze, silver, gold
)

ERRORS_TOTAL = Counter(
    "errors_total",
    "Total number of errors encountered",
    ["pipeline_name", "error_code"],
)


class MetricsCollector:
    """Collects and manages pipeline metrics."""

    def __init__(
        self,
        pipeline_name: str,
        registry: "CollectorRegistry | None" = None,
    ) -> None:
        self.pipeline_name = pipeline_name
        self._registry = registry

    def record_processed(self, layer: str, count: int = 1) -> None:
        """Record processed records for a layer."""
        RECORDS_PROCESSED_TOTAL.labels(
            pipeline_name=self.pipeline_name,
            run_type="default",
            layer=layer,
        ).inc(count)

    def record_error(self, error_code: str) -> None:
        """Record an error occurrence."""
        ERRORS_TOTAL.labels(
            pipeline_name=self.pipeline_name,
            error_code=error_code,
        ).inc()
