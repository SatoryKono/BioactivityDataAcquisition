"""Bootstrap functions for runtime observability components.

Contains bootstrap functions for logging, tracing, metrics, and data quality
monitoring. These functions configure the full observability stack for
pipeline execution.

Unified Observability Contract:
- bootstrap_observability() always returns valid implementations
- Logger: UnifiedLogger with Log Schema enforcement (run_id, pipeline, stage)
- Metrics: PrometheusMetrics or NoOpMetrics (never None)
- Tracer: OpenTelemetryTracer or NoOpTracing (never None)
- DQMonitor: DataQualityMonitor or None (optional)

Note:
    CLI uses NoOp implementations via bootstrap/cli/metrics.py.
    This module provides full observability for runtime execution.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    NoOpMetrics,
    NoOpTracing,
    TracingPort,
)
from bioetl.infrastructure.observability import (
    OpenTelemetryTracer,
    PrometheusMetrics,
    UnifiedLogger,
    start_metrics_server,
)
from bioetl.infrastructure.observability.anomaly import DataQualityMonitor
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

__all__ = [
    "MetricsServerError",
    # Deprecated aliases (backward compatibility)
    "bootstrap_dq_monitor",
    # Canonical names (use these)
    "bootstrap_dq_monitor_port",
    "bootstrap_logger",
    "bootstrap_logger_port",
    "bootstrap_metrics",
    "bootstrap_metrics_port",
    "bootstrap_observability",
    "bootstrap_observability_bundle",
    "bootstrap_tracer",
    "bootstrap_tracer_port",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]


def validate_observability_preflight(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
) -> None:
    """Validate observability components for production readiness.

    Performs preflight validation to detect NoOp implementations in production.
    Emits warnings when observability data will be lost due to NoOp fallbacks.

    This function helps prevent silent data loss in production environments
    where NoOpTracing or NoOpMetrics would discard traces/metrics without
    any visible indication.

    Args:
        tracer: The tracing port implementation (may be NoOpTracing).
        metrics: The metrics port implementation (may be NoOpMetrics).
        environment: Environment name from settings (e.g., "dev", "staging", "prod").
        logger: Logger for emitting warnings.

    Note:
        In non-production environments, NoOp implementations are acceptable
        and no warnings are emitted.
    """
    if environment != "prod":
        return

    if isinstance(tracer, NoOpTracing):
        logger.warning(
            "noop_tracing_in_production",
            message="NoOpTracing in production - traces will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__TRACING_ENABLED=true "
            "and configure OpenTelemetry endpoint",
        )

    if isinstance(metrics, NoOpMetrics):
        logger.warning(
            "noop_metrics_in_production",
            message="NoOpMetrics in production - metrics will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true "
            "to enable Prometheus metrics collection",
        )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Uses UnifiedLogger which enforces the Log Schema from RULES.md §3.2.1:
    - Mandatory fields: run_id, pipeline (bound at initialization)
    - Stage field: defaults to "init" for LoggerPort compatibility

    Layer: Returns domain port implementation (LoggerPort).

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier. If None, generates a new UUID.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        UnifiedLogger implementing LoggerPort with Log Schema enforcement.
    """
    effective_run_id = run_id if run_id is not None else uuid4()
    return UnifiedLogger(
        pipeline=pipeline,
        run_id=effective_run_id,
        log_level=log_level,
        json_format=True,
    )


def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Deprecated: use :func:`bootstrap_logger_port` instead."""
    warnings.warn(
        "bootstrap_logger() is deprecated, use bootstrap_logger_port() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bootstrap_logger_port(pipeline=pipeline, run_id=run_id, log_level=log_level)


def bootstrap_tracer_port(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    When tracing is disabled, returns NoOpTracing.
    When tracing is enabled, returns OpenTelemetryTracer.

    Layer: Returns domain port implementation (TracingPort).

    Args:
        settings: Application settings (MUST be injected, not loaded globally).
        service_name: Name of the service for tracing context.

    Returns:
        TracingPort instance (OpenTelemetryTracer or NoOpTracing).

    Raises:
        ImportError: If tracing is enabled but OpenTelemetry is not installed.
    """
    if settings.observability.tracing_enabled:
        return OpenTelemetryTracer(service_name=service_name)
    return NoOpTracing()


def bootstrap_tracer(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Deprecated: use :func:`bootstrap_tracer_port` instead."""
    warnings.warn(
        "bootstrap_tracer() is deprecated, use bootstrap_tracer_port() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bootstrap_tracer_port(settings=settings, service_name=service_name)


def bootstrap_metrics_port(settings: Settings) -> MetricsPort:
    """Create a metrics port implementation.

    Unified Observability Contract: Always returns a valid MetricsPort.
    When metrics are disabled, returns NoOpMetrics (silent fallback).

    Note:
        This function only creates the metrics collector.
        Server startup is handled separately by entrypoints via
        maybe_start_metrics_server() to keep bootstrap side-effect free.

    Layer: Returns domain port implementation (MetricsPort).

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance (PrometheusMetrics or NoOpMetrics).
        Never returns None - uses NoOpMetrics as fallback.
    """
    if not settings.observability.metrics_enabled:
        # Silent fallback - no warning since explicitly disabled
        return NoOpMetrics(warn_on_use=False)

    return PrometheusMetrics()


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Start metrics server if enabled in settings.

    This function should be called by entrypoints (CLI, REST API) after
    bootstrap to start the Prometheus HTTP server. Separating server
    startup from bootstrap keeps the composition layer side-effect free.

    Args:
        settings: Application settings.

    Returns:
        True if server was started or already running, False if disabled
        or failed to start.

    Raises:
        MetricsServerError: If fail_fast=True and server fails to start.
    """
    if not settings.observability.metrics_enabled:
        return False

    if not settings.observability.metrics_server_enabled:
        return False

    obs = settings.observability

    # Start metrics server - let exceptions propagate to entrypoints
    return start_metrics_server(
        port=settings.metrics_port,
        fail_fast=obs.metrics_fail_fast,
        retry_count=obs.metrics_retry_count,
        retry_delay=obs.metrics_retry_delay,
    )


def bootstrap_metrics(settings: Settings) -> MetricsPort:
    """Deprecated: use :func:`bootstrap_metrics_port` instead."""
    warnings.warn(
        "bootstrap_metrics() is deprecated, use bootstrap_metrics_port() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bootstrap_metrics_port(settings=settings)


def bootstrap_dq_monitor_port(
    settings: Settings, logger: LoggerPort | None = None
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Creates a DataQualityMonitor configured with settings from ObservabilitySettings.
    Returns None if dq_monitor_enabled=False.

    Layer: Returns domain port implementation (DQMonitorPort) or None.

    Args:
        settings: Application settings.
        logger: Optional logger for DQ monitor. If None, uses NoOpLogger.

    Returns:
        Configured DQMonitorPort or None if disabled.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    effective_logger = logger if logger is not None else NoOpLogger()

    monitor = DataQualityMonitor(
        logger=effective_logger,
        baseline_window=obs_settings.dq_baseline_window,
        z_score_threshold=obs_settings.dq_z_score_threshold,
    )

    # Configure min baseline samples
    monitor.detector.min_baseline_samples = obs_settings.dq_min_baseline_samples

    # Set absolute thresholds for critical metrics
    monitor.detector.set_threshold(
        "error_rate",
        min_value=0.0,
        max_value=obs_settings.dq_error_rate_max,
    )
    monitor.detector.set_threshold(
        "quality_score",
        min_value=obs_settings.dq_quality_score_min,
        max_value=1.0,
    )

    return monitor


def bootstrap_dq_monitor(
    settings: Settings, logger: LoggerPort | None = None
) -> DQMonitorPort | None:
    """Deprecated: use :func:`bootstrap_dq_monitor_port` instead."""
    warnings.warn(
        "bootstrap_dq_monitor() is deprecated, use bootstrap_dq_monitor_port() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bootstrap_dq_monitor_port(settings=settings, logger=logger)


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Create a complete observability bundle for pipeline execution.

    Unified Observability Contract:
    - Always returns a valid ObservabilityBundle with non-None logger and metrics
    - Logger: UnifiedLogger with Log Schema enforcement (run_id, pipeline, stage)
    - Fallback to NoOpMetrics when Prometheus is disabled
    - Tracer and DQ monitor remain optional

    Creates a unified observability bundle containing logger, tracer, metrics,
    and data quality monitor.

    Layer: Returns application-level bundle (ObservabilityBundle) containing
    port implementations.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.

    Returns:
        Configured ObservabilityBundle instance with valid implementations.
        Logger and metrics are guaranteed to be non-None.

    Raises:
        ObservabilityContractError: If bundle creation fails validation.
    """
    logger = bootstrap_logger_port(
        pipeline=pipeline, run_id=run_id, log_level=log_level
    )
    tracer = bootstrap_tracer_port(settings)
    metrics = bootstrap_metrics_port(settings)
    dq_monitor = bootstrap_dq_monitor_port(settings, logger)

    bundle = ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    # Log observability initialization status
    logger.info(
        "observability_initialized",
        extra={
            "stage": "bootstrap",
            "metrics_type": type(metrics).__name__,
            "tracer_type": type(tracer).__name__,
            "dq_monitor_enabled": dq_monitor is not None,
        },
    )

    # Preflight validation: warn if NoOp implementations in production
    validate_observability_preflight(
        tracer=tracer,
        metrics=metrics,
        environment=settings.env,
        logger=logger,
    )

    return bundle


def bootstrap_observability(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Deprecated: use :func:`bootstrap_observability_bundle` instead."""
    warnings.warn(
        "bootstrap_observability() is deprecated, use bootstrap_observability_bundle() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bootstrap_observability_bundle(
        pipeline=pipeline, run_id=run_id, settings=settings, log_level=log_level
    )
