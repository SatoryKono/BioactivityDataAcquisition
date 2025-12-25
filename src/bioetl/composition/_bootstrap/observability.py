"""Bootstrap functions for observability components.

Contains bootstrap functions for logging, tracing, metrics, and data quality
monitoring. These functions configure the observability stack for the pipeline.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from bioetl.composition.observability import ObservabilityBundle
from bioetl.infrastructure.observability.logging import (
    create_logger as create_infra_logger,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.server import start_metrics_server
from bioetl.infrastructure.observability.tracing import NoOpTracer, OpenTelemetryTracer

if TYPE_CHECKING:
    from uuid import UUID

    import structlog

    from bioetl.domain.ports import DQMonitorPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_tracer",
]


def bootstrap_logger(
    pipeline: str, run_id: UUID, log_level: str = "INFO"
) -> structlog.BoundLogger:
    """Create a logger for the application layer (e.g., CLI)."""
    return create_infra_logger(
        pipeline=pipeline, run_id=run_id, log_level=log_level, json_format=True
    )


def bootstrap_tracer(service_name: str = "bioetl") -> TracingPort:
    """Bootstrap distributed tracing."""
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    if settings.observability.tracing_enabled:
        try:
            return OpenTelemetryTracer(service_name=service_name)
        except ImportError:
            # OpenTelemetry not installed, fall back to no-op
            pass
    return NoOpTracer()


def bootstrap_metrics(settings: Settings) -> MetricsPort | None:
    """Bootstrap metrics with optional server start.

    Server is started only if explicitly enabled in settings.
    Supports fail_fast mode for strict startup validation.

    Args:
        settings: Application settings.

    Returns:
        MetricsPort instance or None if metrics are disabled.

    Raises:
        MetricsServerError: If fail_fast=True and server fails to start.
    """
    if not settings.observability.metrics_enabled:
        return None

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

    Creates a unified observability bundle containing logger, tracer, metrics,
    and data quality monitor.

    Args:
        pipeline: Pipeline name for logger context.
        run_id: Unique run identifier.
        settings: Application settings.

    Returns:
        Configured ObservabilityBundle instance.
    """
    logger = bootstrap_logger(pipeline=pipeline, run_id=run_id)
    tracer = bootstrap_tracer()
    metrics = bootstrap_metrics(settings)
    dq_monitor = bootstrap_dq_monitor(settings)

    return ObservabilityBundle(
        logger=logger,
        tracer=tracer,
        metrics=metrics,
        dq_monitor=dq_monitor,
    )
