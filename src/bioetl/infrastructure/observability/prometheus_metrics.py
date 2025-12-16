"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.observability.metrics import (
    PIPELINE_DURATION_SECONDS,
    RECORDS_PROCESSED_TOTAL,
)

# Registry of histogram metrics
HISTOGRAMS = {
    "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
}

# Registry of counter metrics
COUNTERS = {
    "records_processed_total": RECORDS_PROCESSED_TOTAL,
}


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Maps metric names to pre-defined Prometheus metrics and records observations.

    Example:
        >>> metrics = PrometheusMetrics()
        >>> metrics.observe_histogram(
        ...     "pipeline_duration_seconds",
        ...     123.45,
        ...     {"pipeline_name": "chembl_activity", "status": "success"}
        ... )
    """

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Observe a value for a Prometheus histogram.

        Args:
            name: The name of the histogram metric (must be in HISTOGRAMS registry).
            value: The value to observe.
            labels: Label values for the metric.

        Raises:
            KeyError: If the metric name is not found in HISTOGRAMS.
        """
        if name in HISTOGRAMS:
            HISTOGRAMS[name].labels(**labels).observe(value)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Increment a Prometheus counter.

        Args:
            name: The name of the counter metric (must be in COUNTERS registry).
            value: The amount to increment by.
            labels: Label values for the metric.

        Raises:
            KeyError: If the metric name is not found in COUNTERS.
        """
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)


class NoOpMetrics(MetricsPort):
    """No-op implementation of MetricsPort for testing."""

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """No-op: does nothing."""
        pass

    def increment_counter(
        self, name: str, value: int, labels: dict[str, str]
    ) -> None:
        """No-op: does nothing."""
        pass
