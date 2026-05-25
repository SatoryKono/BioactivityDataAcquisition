# ruff: noqa: UP049
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


class _HistogramObserver(Protocol):
    def observe(self, _amount: float) -> None: ...


class _CounterObserver(Protocol):
    def inc(self, _amount: float = 1) -> None: ...


class _GaugeObserver(Protocol):
    def set(self, value: float) -> None: ...


class _HistogramMetric(Protocol):
    def labels(self, **labels: str) -> _HistogramObserver: ...


class _CounterMetric(Protocol):
    def labels(self, **labels: str) -> _CounterObserver: ...


class _GaugeMetric(Protocol):
    def labels(self, **labels: str) -> _GaugeObserver: ...


def _require_registered_metric[_MetricT](
    *,
    name: str,
    registry: Mapping[str, _MetricT],
    metric_kind: str,
) -> _MetricT:
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
        counter: _CounterMetric = _require_registered_metric(
            name=name,
            registry=COUNTERS,
            metric_kind="counter",
        )
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
        gauge.labels(**normalize_metric_dispatch_labels(name, resolved_labels)).set(
            value
        )

    def close(self) -> None:
        """Mark the metrics adapter as closed (idempotent)."""
        if self._closed:
            return
        self._closed = True
