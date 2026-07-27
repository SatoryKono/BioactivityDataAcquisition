"""Metrics protocol ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

MetricLabels = dict[str, str]


def resolve_metric_labels(
    labels: MetricLabels | None = None,
) -> MetricLabels:
    """Resolve canonical metric labels.

    Args:
        labels: Canonical metric labels dict.

    Returns:
        Resolved metric labels dict. Returns an empty dict if ``labels`` is None.
    """
    return labels or {}


@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Record an observed value in a histogram metric.

        Args:
            name: Histogram metric name.
            value: Observed numeric value to record.
            labels: Canonical metric labels.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Counter metric name.
            value: Amount to increment the counter by.
            labels: Canonical metric labels.
        """
        ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Gauge metric name.
            value: New gauge value to set.
            labels: Canonical metric labels.
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


@dataclass(frozen=True, slots=True)
class MetricsServerRuntimeStatus:
    """Live metrics server runtime metadata."""

    running: bool
    port: int | None = None
    addr: str | None = None
    started_at: datetime | None = None


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations."""

    def start(
        self,
        port: int,
        addr: str = "0.0.0.0",
        *,
        started_at: datetime | None = None,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics HTTP server on the given port.

        Args:
            port: TCP port to bind the server to.
            addr: Bind address for the HTTP server. Defaults to ``0.0.0.0``.
            started_at: Explicit application-owned startup timestamp for runtime
                status bookkeeping.
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

    def get_runtime_status(self) -> MetricsServerRuntimeStatus:
        """Return the current in-process metrics server runtime metadata."""
        ...

    def reset(self) -> None:
        """Reset all collected metric values to their initial state."""
        ...


@runtime_checkable
class MetricsPublisherPort(Protocol):
    """Protocol for explicit metrics publication workflows."""

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> bool:
        """Publish the current metrics snapshot to a gateway backend."""
        ...

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
    ) -> bool:
        """Delete the current bounded metrics snapshot from a gateway backend."""
        ...


@runtime_checkable
class HealthMetricsExpositionPort(Protocol):
    """Port for Prometheus text exposition on the health-server scrape path."""

    def build_exposition(self) -> str:
        """Return Prometheus text exposition body for ``GET /metrics``."""
        ...
