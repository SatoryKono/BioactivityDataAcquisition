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

    Args:
        labels: Canonical metric labels dict (highest precedence).
        _labels: Legacy ``_labels`` alias (second precedence).
        tags: Legacy ``tags`` alias (lowest precedence).

    Returns:
        Resolved metric labels dict. Returns an empty dict if all inputs are None.
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
    ) -> None:
        """Record an observed value in a histogram metric.

        Args:
            name: Histogram metric name.
            value: Observed numeric value to record.
            labels: Canonical metric labels.
            _labels: Legacy labels alias (lower precedence than labels).
            tags: Legacy tags alias (lowest precedence).
        """
        ...

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
            name: Counter metric name.
            value: Amount to increment the counter by.
            labels: Canonical metric labels.
            _labels: Legacy labels alias (lower precedence than labels).
            tags: Legacy tags alias (lowest precedence).
        """
        ...

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
            name: Gauge metric name.
            value: New gauge value to set.
            labels: Canonical metric labels.
            _labels: Legacy labels alias (lower precedence than labels).
            tags: Legacy tags alias (lowest precedence).
        """
        ...

    def close(self) -> None:
        """Flush pending metrics and release backend resources."""
        ...


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
        addr: str = "0.0.0.0",
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics HTTP server on the given port.

        Args:
            port: TCP port to bind the server to.
            addr: Bind address for the HTTP server. Defaults to ``0.0.0.0``.
            fail_fast: If True, raise immediately on bind failure instead of retrying.
            retry_count: Number of times to retry on transient bind errors. Defaults to 3.
            retry_delay: Seconds to wait between retries. Defaults to 1.0.

        Returns:
            True if the server started successfully, False otherwise.
        """
        ...

    def is_running(self) -> bool:
        """Return True if the metrics server is currently accepting connections."""
        ...

    def reset(self) -> None:
        """Reset all collected metric values to their initial state."""
        ...
