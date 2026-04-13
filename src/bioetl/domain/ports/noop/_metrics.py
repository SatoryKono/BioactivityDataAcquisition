"""No-op metrics implementation."""

from __future__ import annotations

from bioetl.domain.ports.observability.metrics import MetricLabels


class NoOpMetrics:
    """No-op implementation of MetricsPort."""

    _warned: bool = False

    def __init__(self, warn_on_use: bool = False) -> None:
        """Initialize the no-op metrics sink.

        Args:
            warn_on_use: If True, emit a one-time UserWarning on first instantiation
                to alert developers that metrics are not being collected.
        """
        if warn_on_use and not NoOpMetrics._warned:
            import warnings

            warnings.warn(
                "NoOpMetrics is being used - metrics are NOT being collected. "
                "Set BIOETL_METRICS_ENABLED=true or inject PrometheusMetrics "
                "to enable metrics collection.",
                UserWarning,
                stacklevel=2,
            )
            NoOpMetrics._warned = True

    @classmethod
    def reset_warning(cls) -> None:
        """Reset the class-level warning flag to allow re-emission of the usage warning."""
        cls._warned = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """No-op implementation — discards the histogram observation.

        Args:
            name: Metric name (ignored).
            value: Observed value (ignored).
            labels: Canonical metric labels (ignored).
        """
        del name, value, labels
        return None

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
    ) -> None:
        """No-op implementation — discards the counter increment.

        Args:
            name: Counter metric name (ignored).
            value: Increment value (ignored).
            labels: Canonical metric labels (ignored).
        """
        del name, value, labels
        return None

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """No-op implementation — discards the gauge value.

        Args:
            name: Gauge metric name (ignored).
            value: Gauge value to set (ignored).
            labels: Canonical metric labels (ignored).
        """
        del name, value, labels
        return None

    def close(self) -> None:
        """No-op implementation — no metrics backend to flush or close."""
        return None
