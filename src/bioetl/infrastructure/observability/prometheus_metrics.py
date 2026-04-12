"""Prometheus Metrics adapter implementing MetricsPort.

Provides concrete implementation of the MetricsPort interface using
Prometheus client library.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeVar

from bioetl.domain.observability_metric_names import (
    canonicalize_observability_metric_name,
)
from bioetl.domain.ports import MetricLabels, MetricsPort, resolve_metric_labels
from bioetl.infrastructure.observability.prometheus_metric_label_policies import (
    normalize_metric_dispatch_labels,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)

__all__ = ["COUNTERS", "GAUGES", "HISTOGRAMS", "PrometheusMetrics"]


class _HistogramObserver(Protocol):
    def observe(self, amount: float) -> None: ...


class _CounterObserver(Protocol):
    def inc(self, amount: float = 1) -> None: ...


class _GaugeObserver(Protocol):
    def set(self, value: float) -> None: ...


class _HistogramMetric(Protocol):
    def labels(self, **labels: str) -> _HistogramObserver: ...


class _CounterMetric(Protocol):
    def labels(self, **labels: str) -> _CounterObserver: ...


class _GaugeMetric(Protocol):
    def labels(self, **labels: str) -> _GaugeObserver: ...


_MetricT = TypeVar("_MetricT")


def _resolve_registered_metric_name(
    *,
    name: str,
    registry: Mapping[str, object],
) -> str:
    """Resolve one metric name against canonical and legacy registry keys."""
    if name in registry:
        return name
    canonical_name = canonicalize_observability_metric_name(name)
    if canonical_name in registry:
        return canonical_name
    return name


def _require_registered_metric(
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
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Record a histogram observation for the named metric.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        resolved_name = _resolve_registered_metric_name(name=name, registry=HISTOGRAMS)
        histogram: _HistogramMetric = _require_registered_metric(
            name=resolved_name,
            registry=HISTOGRAMS,
            metric_kind="histogram",
        )
        histogram.labels(
            **normalize_metric_dispatch_labels(resolved_name, resolved_labels)
        ).observe(value)

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        resolved_name = _resolve_registered_metric_name(name=name, registry=COUNTERS)
        counter: _CounterMetric = _require_registered_metric(
            name=resolved_name,
            registry=COUNTERS,
            metric_kind="counter",
        )
        counter.labels(
            **normalize_metric_dispatch_labels(resolved_name, resolved_labels)
        ).inc(value)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Identifier name.
            value: Input value.
            labels: Labels dict (primary parameter).
            _labels: Alias for labels (backward compatibility).
            tags: Alias for labels (alternative naming convention).
        """
        resolved_labels = resolve_metric_labels(
            labels,
            _labels=_labels,
            tags=tags,
        )
        resolved_name = _resolve_registered_metric_name(name=name, registry=GAUGES)
        gauge: _GaugeMetric = _require_registered_metric(
            name=resolved_name,
            registry=GAUGES,
            metric_kind="gauge",
        )
        gauge.labels(
            **normalize_metric_dispatch_labels(resolved_name, resolved_labels)
        ).set(value)

    def close(self) -> None:
        """Mark the metrics adapter as closed (idempotent)."""
        if self._closed:
            return
        self._closed = True
