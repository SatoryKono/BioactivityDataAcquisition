"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.observability.metrics import (
    BATCH_SIZE_RECORDS,
    CIRCUIT_BREAKER_FAILURE_TOTAL,
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_SUCCESS_TOTAL,
    CIRCUIT_BREAKER_TRIPS_TOTAL,
    DQ_RECORDS_QUARANTINED_TOTAL,
    ERRORS_TOTAL,
    FILTER_IDS_DUPLICATES_TOTAL,
    FILTER_IDS_LOADED_TOTAL,
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
    "filter_ids_loaded_total": FILTER_IDS_LOADED_TOTAL,
    "filter_ids_duplicates_total": FILTER_IDS_DUPLICATES_TOTAL,
    "dq_records_quarantined_total": DQ_RECORDS_QUARANTINED_TOTAL,
    "circuit_breaker_trips_total": CIRCUIT_BREAKER_TRIPS_TOTAL,
    "circuit_breaker_success_total": CIRCUIT_BREAKER_SUCCESS_TOTAL,
    "circuit_breaker_failure_total": CIRCUIT_BREAKER_FAILURE_TOTAL,
}

# Registry of gauge metrics
GAUGES = {
    "circuit_breaker_state": CIRCUIT_BREAKER_STATE,
}


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Maps metric names to pre-defined Prometheus metrics and records observations.
    """

    def __init__(self) -> None:
        """Initialize Prometheus metrics adapter."""
        self._closed = False

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

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Set a Prometheus gauge to a specific value."""
        if name in GAUGES:
            GAUGES[name].labels(**labels).set(value)

    def close(self) -> None:
        """Cleanup Prometheus metrics. Idempotent.

        Note: For the default global REGISTRY, this is a no-op since
        metrics are shared across the process. For custom registries,
        this could unregister collectors.
        """
        if self._closed:
            return
        # For default REGISTRY: no-op (shared across tests/process)
        # If using custom registry, could call registry.unregister() here
        self._closed = True


class NoOpMetrics(MetricsPort):
    """Null object pattern for metrics (used when Prometheus is disabled)."""

    def __init__(self) -> None:
        """Initialize no-op metrics."""
        self._closed = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """No-op histogram observation."""
        pass

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """No-op counter increment."""
        pass

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """No-op gauge set."""
        pass

    def close(self) -> None:
        """No-op close. Idempotent."""
        self._closed = True
