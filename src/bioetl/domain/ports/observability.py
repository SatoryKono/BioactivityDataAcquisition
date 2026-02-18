"""Observability ports for tracing, metrics, and logging.

This module contains ports for distributed tracing, metrics collection,
and structured logging.

Design Decision — TracingPort as OpenTelemetry facade:
    TracingPort is intentionally modeled after the OpenTelemetry Tracing API.
    ``get_tracer()`` returns an object whose interface mirrors
    ``opentelemetry.trace.Tracer`` (``start_as_current_span``, span context
    manager, ``set_attribute``, ``record_exception``).  This is a deliberate
    architectural choice (see ADR-017, ADR-022):

    * The OTel API is a vendor-neutral industry standard for distributed tracing.
    * Adopting its surface as our port contract avoids inventing a bespoke
      tracing abstraction and keeps the migration path to real OTel trivial.
    * NoOp implementations (``_NoOpOtelTracer``, ``_NoOpSpan``) mirror the same
      API surface so that application code uses a single calling convention
      regardless of whether tracing is enabled.
"""

from __future__ import annotations

from typing import Any, Protocol, Self, runtime_checkable


@runtime_checkable
class TracingPort(Protocol):
    """Port for distributed tracing — an OpenTelemetry Tracing API facade.

    This port is **deliberately** shaped after the OpenTelemetry API so that:

    1. Application code calls ``tracer.get_tracer(name).start_as_current_span(...)``
       — the standard OTel calling convention — regardless of the backend.
    2. Switching from ``NoOpTracing`` to ``OpenTelemetryTracer`` requires zero
       changes in application/domain code; only composition wiring changes.
    3. Any OTel-compatible tracer (Jaeger, Zipkin, OTLP) can be plugged in
       without altering the port contract.

    The ``Any`` return type of ``get_tracer`` is intentional: it represents an
    ``opentelemetry.trace.Tracer``-compatible object.  Using ``Any`` avoids a
    hard dependency on the ``opentelemetry`` package in the domain layer while
    preserving the OTel calling convention in all implementations (including
    ``NoOpTracing``).

    See Also:
        - ADR-017: Observability Architecture — establishes port-based tracing.
        - ADR-022: NoOp Tracing — documents the OTel facade rationale and
          NoOp default for local-only deployment.
    """

    def get_tracer(self, name: str) -> Any:  # Any: OTel Tracer (avoids op...
        """Return an OpenTelemetry-compatible tracer instance.

        The returned object exposes ``start_as_current_span(name, attributes=...)``
        — the standard OTel ``Tracer`` interface.  For ``NoOpTracing`` this is a
        lightweight no-op; for ``OpenTelemetryTracer`` it delegates to the real
        OTel SDK.

        Args:
            name: Instrumentation scope name (e.g. ``"bioetl.pipeline"``).

        Returns:
            An OTel-compatible tracer (concrete type depends on the implementation).
        """
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

    def bind(self, **kwargs: Any) -> Self:  # Any: structlog-compatible a...
        """Bind additional context to the logger.

        Returns a new logger instance with the bound context.
        """
        ...

    def info(self, _event: str, **kwargs: Any) -> Any:  # Any: structlog-compatible a...
        """Log an informational message."""
        ...

    # Any: structlog-compatible a...
    def warning(self, _event: str, **kwargs: Any) -> Any:
        """Log a warning message."""
        ...

    # Any: structlog-compatible a...
    def error(self, _event: str, **kwargs: Any) -> Any:
        """Log an error message."""
        ...

    # Any: structlog-compatible a...
    def debug(self, _event: str, **kwargs: Any) -> Any:
        """Log a debug message."""
        ...

    # Any: structlog-compatible a...
    def exception(self, _event: str, **kwargs: Any) -> Any:
        """Log an exception with traceback."""
        ...


@runtime_checkable
class DQMonitorPort(Protocol):
    """Port for data quality monitoring and anomaly detection.

    Monitors pipeline metrics for statistical anomalies using
    Z-score analysis and configurable thresholds. Detects spikes,
    drops, and threshold breaches in pipeline metrics.

    Example:
        Basic monitoring in a pipeline::

            # DataQualityMonitor is injected via composition layer
            # (see: infrastructure.observability.anomaly.DataQualityMonitor)
            monitor: DQMonitorPort = injected_monitor

            # Register metrics with historical baseline
            monitor.add_metric(
                "record_count",
                baseline=[1000, 1050, 980, 1020, 990, 1010, 1005],
            )
            monitor.add_metric(
                "error_rate",
                baseline=[0.01, 0.02, 0.015, 0.01, 0.02],
                max_threshold=0.10,  # Hard limit: fail if > 10%
            )

            # After pipeline run, check for anomalies
            anomalies = monitor.check_quality({
                "record_count": 500,   # Suspicious drop!
                "error_rate": 0.15,    # Exceeds threshold!
            })

            for anomaly in anomalies:
                logger.warning(
                    "data_quality_anomaly_detected",
                    metric=anomaly.metric_name,
                    severity=anomaly.severity.value,
                    current=anomaly.current_value,
                    baseline_mean=anomaly.baseline_mean,
                    z_score=anomaly.z_score,
                    message=anomaly.message,
                )

            # Update baseline only if no critical issues
            monitor.update_baseline_from_metrics({
                "record_count": 1000,
                "error_rate": 0.02,
            })

    See Also:
        - ``DataQualityMonitor`` - Implementation in infrastructure layer
        - ``Anomaly`` - Detected anomaly data structure
        - ``AnomalySeverity`` - LOW, MEDIUM, HIGH, CRITICAL levels
    """

    def add_metric(
        self,
        metric_name: str,
        baseline: Any,  # Any: Sequence[float] (avoid...
        min_threshold: float | None = None,
        max_threshold: float | None = None,
    ) -> None:
        """Register metric with historical baseline and thresholds.

        Args:
            metric_name: Name of the metric (e.g., "record_count", "error_rate")
            baseline: Historical values for baseline calculation
            min_threshold: Absolute minimum threshold (optional)
            max_threshold: Absolute maximum threshold (optional)

        Example:
            Register common pipeline metrics::

                # Record count with historical data (7-day baseline)
                monitor.add_metric(
                    "record_count",
                    baseline=[1000, 1050, 980, 1020, 990, 1010, 1005],
                )

                # Error rate with hard threshold (fail if > 10%)
                monitor.add_metric(
                    "error_rate",
                    baseline=[0.01, 0.02, 0.015],
                    max_threshold=0.10,
                )

                # Quality score with minimum threshold
                monitor.add_metric(
                    "quality_score",
                    baseline=[0.95, 0.97, 0.96],
                    min_threshold=0.80,  # Alert if below 80%
                )
        """
        ...

    def check_quality(
        self,
        metrics: dict[str, float],
    ) -> list[Any]:  # Any: list[Anomaly] (avoids importing Anomaly in domain port)
        """Check current metrics against baseline for anomalies.

        Args:
            metrics: Current metric values to check

        Returns:
            List of detected anomalies (empty if none detected)

        Example:
            Check metrics after pipeline run::

                anomalies = monitor.check_quality({
                    "record_count": 500,    # May trigger DROP anomaly
                    "error_rate": 0.15,     # May trigger THRESHOLD_EXCEEDED
                    "processing_time_ms": 5000,
                })

                if anomalies:
                    critical = [a for a in anomalies if a.severity.value == "critical"]
                    if critical:
                        raise DataQualityError(f"Critical anomalies: {critical}")

                    for anomaly in anomalies:
                        # Log non-critical anomalies as warnings
                        logger.warning(str(anomaly))
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

        Example:
            Update baseline after successful run::

                # Only update baseline if run was successful
                if run_result.success:
                    monitor.update_baseline_from_metrics({
                        "record_count": run_result.record_count,
                        "error_rate": run_result.error_rate,
                        "processing_time_ms": run_result.duration_ms,
                    })
                    # Note: If metrics contain critical anomalies,
                    # baseline will NOT be updated (protects from bad data)
        """
        ...

    def get_baseline_stats(
        self,
        metric_name: str,
    ) -> tuple[float, float, int] | None:
        """Get baseline statistics for a metric.

        Returns:
            Tuple of (mean, stddev, sample_count) or None if no baseline

        Example:
            Inspect baseline for debugging::

                stats = monitor.get_baseline_stats("record_count")
                if stats:
                    mean, stddev, count = stats
                    logger.info(
                        "baseline_stats",
                        metric="record_count",
                        mean=mean,
                        stddev=stddev,
                        sample_count=count,
                    )
                    # Calculate expected range (mean ± 2.5 * stddev)
                    lower = mean - 2.5 * stddev
                    upper = mean + 2.5 * stddev
                    logger.info(f"Expected range: [{lower:.0f}, {upper:.0f}]")
                else:
                    logger.warning("No baseline data for record_count")
        """
        ...
