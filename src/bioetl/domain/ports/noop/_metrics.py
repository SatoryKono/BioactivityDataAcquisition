"""No-op metrics implementation."""

from __future__ import annotations

from bioetl.domain.ports.observability.metrics import (
    MetricLabels,
    resolve_metric_labels,
)


class NoOpMetrics:
    """No-op implementation of MetricsPort."""

    _warned: bool = False

    def __init__(self, warn_on_use: bool = False) -> None:
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
        cls._warned = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        del name, value, resolved_labels
        return None

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        del name, value, resolved_labels
        return None

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        del name, value, resolved_labels
        return None

    def inc_quarantine_records(
        self,
        _pipeline: str,
        _reason: str,
        _count: int = 1,
    ) -> None:
        return None

    def inc_dq_validation_failures(
        self,
        _pipeline: str,
        _stage: str,
        _severity: str,
        _count: int = 1,
    ) -> None:
        return None

    def close(self) -> None:
        return None
