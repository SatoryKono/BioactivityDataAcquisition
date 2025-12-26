"""Bootstrap functions for observability components.

Contains bootstrap functions for logging, tracing, metrics, and data quality
monitoring. These functions configure the observability stack for the pipeline.

Unified Observability Contract:
- bootstrap_observability() always returns valid implementations
- Logger: StructlogLogger (always valid)
- Metrics: PrometheusMetrics or NoOpMetrics (never None)
- Tracer: OpenTelemetryTracer or NoOpTracing (never None)
- DQMonitor: DataQualityMonitor or None (optional)
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import structlog

from bioetl.composition.observability import ObservabilityBundle
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.server import start_metrics_server
from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer

if TYPE_CHECKING:
    from uuid import UUID

    from bioetl.domain.ports import DQMonitorPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_tracer",
    "validate_observability_preflight",
]


def validate_observability_preflight(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: structlog.BoundLogger,
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


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


def bootstrap_tracer(service_name: str = "bioetl") -> TracingPort:
    """Bootstrap distributed tracing.

    Unified Observability Contract: Always returns a valid TracingPort.
    When tracing is disabled or OpenTelemetry is not installed,
    returns NoOpTracing (silent fallback).

    Args:
        service_name: Name of the service for tracing context.

    Returns:
        TracingPort instance (OpenTelemetryTracer or NoOpTracing).
        Never returns None - uses NoOpTracing as fallback.
    """
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    if settings.observability.tracing_enabled:
        try:
            return OpenTelemetryTracer(service_name=service_name)
        except ImportError:
            # OpenTelemetry not installed, fall back to no-op
            pass
    return NoOpTracing()


def bootstrap_metrics(settings: Settings) -> MetricsPort:
    """Bootstrap metrics with optional server start.

    Unified Observability Contract: Always returns a valid MetricsPort.
    When metrics are disabled, returns NoOpMetrics (silent fallback).

    Server is started only if explicitly enabled in settings.
    Supports fail_fast mode for strict startup validation.

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance (PrometheusMetrics or NoOpMetrics).
        Never returns None - uses NoOpMetrics as fallback.

    Raises:
        MetricsServerError: If fail_fast=True and server fails to start.
    """
    if not settings.observability.metrics_enabled:
        # Silent fallback - no warning since explicitly disabled
        return NoOpMetrics(warn_on_use=False)

    metrics = PrometheusMetrics()

    if settings.observability.metrics_server_enabled:
        obs = settings.observability

        if obs.metrics_fail_fast:
            # In fail_fast mode, let MetricsServerError propagate
            start_metrics_server(
                port=settings.metrics_port,
                fail_fast=True,
                retry_count=obs.metrics_retry_count,
                retry_delay=obs.metrics_retry_delay,
            )
        else:
            # Lenient mode: log but don't fail - metrics collection still works
            with contextlib.suppress(Exception):
                start_metrics_server(
                    port=settings.metrics_port,
                    fail_fast=False,
                    retry_count=obs.metrics_retry_count,
                    retry_delay=obs.metrics_retry_delay,
                )

    return metrics


def bootstrap_dq_monitor(settings: Settings) -> DQMonitorPort | None:
    """Bootstrap data quality monitor for anomaly detection.

    Creates a DataQualityMonitor configured with settings from ObservabilitySettings.
    Returns None if dq_monitor_enabled=False.

    Args:
        settings: Application settings.

    Returns:
        Configured DQMonitorPort or None if disabled.
    """
    obs_settings = settings.observability

    if not obs_settings.dq_monitor_enabled:
        return None

    from bioetl.infrastructure.observability.anomaly import DataQualityMonitor

    monitor = DataQualityMonitor(
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


def bootstrap_observability(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
) -> ObservabilityBundle:
    """Bootstrap all observability components.

    Unified Observability Contract:
    - Always returns a valid ObservabilityBundle with non-None logger and metrics
    - Fallback to StructlogLogger + NoOpMetrics when Prometheus is disabled
    - Tracer and DQ monitor remain optional

    Creates a unified observability bundle containing logger, tracer, metrics,
    and data quality monitor.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.

    Returns:
        Configured ObservabilityBundle instance with valid implementations.
        Logger and metrics are guaranteed to be non-None.

    Raises:
        ObservabilityContractError: If bundle creation fails validation.
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=run_id)
    tracer = bootstrap_tracer()
    metrics = bootstrap_metrics(settings)
    dq_monitor = bootstrap_dq_monitor(settings)

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
