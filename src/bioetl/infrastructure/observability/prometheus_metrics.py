"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from bioetl.domain.ports import MetricLabels, MetricsPort, resolve_metric_labels
from bioetl.infrastructure.observability.prometheus_metric_label_dispatch import (
    normalize_metric_dispatch_labels,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

__all__ = ["COUNTERS", "GAUGES", "HISTOGRAMS", "PrometheusMetrics"]

# Compatibility aliases kept at the adapter boundary while callers migrate to
# the exposition-contract `_total` suffix used by the registered Counter.
_COUNTER_ALIASES = {
    "bioetl_dq_anomaly_detected": "bioetl_dq_anomaly_detected_total",
    "bioetl_dq_soft_threshold_exceeded": "bioetl_dq_soft_threshold_exceeded_total",
    "bioetl_dq_baseline_updated": "bioetl_dq_baseline_updated_total",
    "bioetl_shutdown_initiated": "bioetl_shutdown_initiated_total",
    "bioetl_shutdown_completed": "bioetl_shutdown_completed_total",
}


class _HistogramObserver(Protocol):
    def observe(self, amount: float) -> None:
        del amount


class _CounterObserver(Protocol):
    def inc(self, amount: float = 1) -> None:
        del amount


class _GaugeObserver(Protocol):
    def set(self, value: float) -> None: ...


class _HistogramMetric(Protocol):
    def labels(self, **labels: str) -> _HistogramObserver: ...

    def observe(self, amount: float) -> None:
        del amount


class _CounterMetric(Protocol):
    def labels(self, **labels: str) -> _CounterObserver: ...

    def inc(self, amount: float = 1) -> None:
        del amount


class _GaugeMetric(Protocol):
    def labels(self, **labels: str) -> _GaugeObserver: ...

    def set(self, value: float) -> None: ...


def _has_declared_labels(metric: object) -> bool | None:
    labelnames = getattr(metric, "_labelnames", None)
    if isinstance(labelnames, tuple | list):
        return bool(labelnames)
    return None


def _reject_unexpected_labels(name: str, labels: MetricLabels) -> None:
    if labels:
        formatted = ", ".join(sorted(labels))
        raise ValueError(
            f"Prometheus metric {name} does not accept labels: {formatted}"
        )


def _require_registered_metric[MetricT](
    *,
    name: str,
    registry: Mapping[str, MetricT],
    metric_kind: str,
) -> MetricT:
    """Return a registered metric or fail loudly on contract drift."""
    metric = registry.get(name)
    if metric is None:
        raise ValueError(
            f"Unknown Prometheus {metric_kind} metric: {name}. "
            f"Register it before emitting runtime observability signals."
        )
    return metric


class PrometheusMetrics(MetricsPort):
    """Prometheus implementation of MetricsPort.

    Uses the generic MetricsPort API with standardized metric names that map
    into ``HISTOGRAMS``, ``COUNTERS``, and ``GAUGES`` registries.

    Extension rule: add new metric definitions in
    ``infrastructure/observability/metrics.py`` and register them in this
    module, rather than creating duplicate domain-level metrics interfaces.
    """

    def __init__(self) -> None:
        self._closed = False

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Record a histogram observation for the named metric.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Canonical labels dict.
        """
        resolved_labels = resolve_metric_labels(labels)
        histogram: _HistogramMetric = _require_registered_metric(
            name=name,
            registry=HISTOGRAMS,
            metric_kind="histogram",
        )
        if _has_declared_labels(histogram) is False:
            _reject_unexpected_labels(name, resolved_labels)
            histogram.observe(value)
            return
        histogram.labels(
            **normalize_metric_dispatch_labels(name, resolved_labels)
        ).observe(value)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Canonical labels dict.
        """
        resolved_labels = resolve_metric_labels(labels)
        name = _COUNTER_ALIASES.get(name, name)
        counter: _CounterMetric = _require_registered_metric(
            name=name,
            registry=COUNTERS,
            metric_kind="counter",
        )
        if _has_declared_labels(counter) is False:
            _reject_unexpected_labels(name, resolved_labels)
            counter.inc(value)
            return
        counter.labels(**normalize_metric_dispatch_labels(name, resolved_labels)).inc(
            value
        )

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Canonical labels dict.
        """
        resolved_labels = resolve_metric_labels(labels)
        gauge: _GaugeMetric = _require_registered_metric(
            name=name,
            registry=GAUGES,
            metric_kind="gauge",
        )
        if _has_declared_labels(gauge) is False:
            _reject_unexpected_labels(name, resolved_labels)
            gauge.set(value)
            return
        gauge.labels(**normalize_metric_dispatch_labels(name, resolved_labels)).set(
            value
        )

    def close(self) -> None:
        """Mark the metrics adapter as closed (idempotent)."""
        if self._closed:
            return
        self._closed = True
