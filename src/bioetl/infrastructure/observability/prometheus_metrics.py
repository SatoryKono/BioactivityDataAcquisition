"""Prometheus implementation of MetricsPort."""

from __future__ import annotations

from bioetl.infrastructure.observability.metrics import (
    PIPELINE_DURATION_SECONDS,
    RECORDS_PROCESSED_TOTAL,
)

# Mapping of metric names to Prometheus objects
HISTOGRAMS = {
    "pipeline_duration_seconds": PIPELINE_DURATION_SECONDS,
}

COUNTERS = {
    "records_processed_total": RECORDS_PROCESSED_TOTAL,
}


class PrometheusMetrics:
    """Prometheus implementation of MetricsPort."""

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """Record a histogram observation."""
        HISTOGRAMS[name].labels(**labels).observe(value)

    def increment_counter(
        self, name: str, value: int, labels: dict[str, str]
    ) -> None:
        """Increment a counter metric."""
        COUNTERS[name].labels(**labels).inc(value)


class NoOpMetrics:
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
