"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.observability.metrics import (
    BATCH_SIZE_RECORDS,
    ERRORS_TOTAL,
    PIPELINE_DURATION_SECONDS,
    RECORDS_PROCESSED_TOTAL,
)

# Registry of histogram metrics
HISTOGRAMS = {
    "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
    "batch_size_records": BATCH_SIZE_RECORDS,
}

# Registry of counter metrics
COUNTERS = {
    "records_processed_total": RECORDS_PROCESSED_TOTAL,
    "errors_total": ERRORS_TOTAL,
}


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Maps metric names to pre-defined Prometheus metrics and records observations.
    """

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Observe a value for a Prometheus histogram."""
        if name in HISTOGRAMS:
            HISTOGRAMS[name].labels(**labels).observe(value)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Increment a Prometheus counter."""
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)
