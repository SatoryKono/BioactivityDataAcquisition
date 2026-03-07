"""Metrics protocol ports."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

MetricLabels = dict[str, str]


def resolve_metric_labels(
    labels: MetricLabels | None = None,
    *,
    _labels: MetricLabels | None = None,
    tags: MetricLabels | None = None,
) -> MetricLabels:
    """Resolve canonical labels with legacy alias compatibility.

    Precedence order is explicit ``labels`` > legacy ``_labels`` > legacy ``tags``.
    """
    if labels is not None:
        return labels
    if _labels is not None:
        return _labels
    if tags is not None:
        return tags
    return {}


@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None: ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None: ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
        *,
        _labels: MetricLabels | None = None,
        tags: MetricLabels | None = None,
    ) -> None: ...

    def inc_quarantine_records(
        self,
        pipeline: str,
        reason: str,
        count: int = 1,
    ) -> None: ...

    def inc_dq_validation_failures(
        self,
        pipeline: str,
        stage: str,
        severity: str,
        count: int = 1,
    ) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class ExecutorMetricsPort(Protocol):
    """Protocol for executors providing batch metrics."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations."""

    def start(
        self,
        port: int,
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool: ...

    def is_running(self) -> bool: ...

    def reset(self) -> None: ...
