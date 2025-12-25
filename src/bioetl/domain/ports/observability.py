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
