"""Observability ports for tracing, metrics, and logging.

This module contains ports for distributed tracing (OpenTelemetry),
metrics collection, and structured logging.
"""

from __future__ import annotations

from typing import Any, Protocol, Self, runtime_checkable


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing (OpenTelemetry).

    Abstracts the tracer implementation to allow no-op or specific backends.
    """

    def get_tracer(self, name: str) -> Any:
        """Get a tracer instance for instrumentation."""
        ...

    def close(self) -> None:
        """Flush pending spans and cleanup tracing resources.

        This method should be called when the pipeline is shutting down
        to ensure all spans are exported before the process exits.
        The implementation MUST be idempotent (safe to call multiple times).
        """
        ...


@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection.

    This interface abstracts the metrics collection mechanism, allowing the
    application to record metrics without knowing the specific implementation
    (e.g., Prometheus, StatsD, CloudWatch).

    Note: MetricsPort uses synchronous methods for low-overhead operations.
    Unlike I/O ports, metric collection should be fast and non-blocking
    by design (using thread-safe counters, not I/O).
    """

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Observe a value for a histogram metric.

        Args:
            name: The name of the histogram metric.
            value: The value to observe.
            labels: A dictionary of label names to label values.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: dict[str, str],
    ) -> None:
        """Increment a counter metric.

        Args:
            name: The name of the counter metric.
            value: The amount to increment by.
            labels: A dictionary of label names to label values.
        """
        ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str],
    ) -> None:
        """Set a gauge metric to a specific value.

        Args:
            name: The name of the gauge metric.
            value: The value to set.
            labels: A dictionary of label names to label values.
        """
        ...

    def close(self) -> None:
        """Cleanup metrics resources.

        This method should be called when the pipeline is shutting down
        to properly release any resources held by the metrics implementation.
        The implementation MUST be idempotent (safe to call multiple times).
        """
        ...


@runtime_checkable
class LoggerPort(Protocol):
    """Port for structured logging.

    This interface abstracts the logging mechanism, allowing the application
    to log messages without depending on a specific logging library
    (e.g., structlog, loguru, stdlib logging).

    Note: LoggerPort uses synchronous methods as logging operations
    should be fast and non-blocking by design.
    """

    def bind(self, **kwargs: Any) -> Self:
        """Bind additional context to the logger.

        Returns a new logger instance with the bound context.
        """
        ...

    def info(self, _event: str, **kwargs: Any) -> Any:
        """Log an informational message."""
        ...

    def warning(self, _event: str, **kwargs: Any) -> Any:
        """Log a warning message."""
        ...

    def error(self, _event: str, **kwargs: Any) -> Any:
        """Log an error message."""
        ...

    def debug(self, _event: str, **kwargs: Any) -> Any:
        """Log a debug message."""
        ...

    def exception(self, _event: str, **kwargs: Any) -> Any:
        """Log an exception with traceback."""
        ...


@runtime_checkable
class DQMonitorPort(Protocol):
    """Port for data quality monitoring and anomaly detection.

    Monitors pipeline metrics for statistical anomalies using
    Z-score analysis and configurable thresholds.

    Example:
        >>> monitor = DataQualityMonitor(z_score_threshold=2.5)
        >>> anomalies = monitor.check_quality({
        ...     "record_count": 1000,
        ...     "error_rate": 0.15,
        ... })
        >>> for a in anomalies:
        ...     print(f"{a.severity}: {a.message}")
    """

    def add_metric(
        self,
        metric_name: str,
        baseline: Any,  # Sequence[float]
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        """Register metric with historical baseline and thresholds.

        Args:
            metric_name: Name of the metric (e.g., "record_count", "error_rate")
            baseline: Historical values for baseline calculation
            min_threshold: Absolute minimum threshold (optional)
            max_threshold: Absolute maximum threshold (optional)
        """
        ...

    def check_quality(
        self,
        metrics: dict[str, float],
    ) -> list[Any]:
        """Check current metrics against baseline for anomalies.

        Args:
            metrics: Current metric values to check

        Returns:
            List of detected anomalies (empty if none detected)
        """
        ...

    def update_baseline_from_metrics(
        self,
        metrics: dict[str, float],
    ) -> None:
        """Update baseline with current metrics.

        Skips update if critical anomalies were detected to avoid
        polluting baseline with bad data.

        Args:
            metrics: Current metric values to add to baseline
        """
        ...

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None:
        """Get baseline statistics for a metric.

        Returns:
            Tuple of (mean, stddev, sample_count) or None if no baseline
        """
        ...
