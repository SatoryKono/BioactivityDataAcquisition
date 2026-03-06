"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    NoOpMetrics,
    NoOpTracing,
    TracingPort,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from bioetl.domain.ports import DQMonitorPort
    from bioetl.infrastructure.config import Settings

__all__ = [
    "bootstrap_observability_bundle_impl",
    "validate_observability_preflight_impl",
]


def validate_observability_preflight_impl(
    *,
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
) -> None:
    """Validate observability components for production readiness."""
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


def bootstrap_observability_bundle_impl(
    *,
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str,
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort],
    tracer_bootstrapper: Callable[[Settings], TracingPort],
    metrics_bootstrapper: Callable[[Settings], MetricsPort],
    dq_monitor_bootstrapper: Callable[
        [Settings, LoggerPort | None], DQMonitorPort | None
    ],
    preflight_validator: Callable[[TracingPort, MetricsPort, str, LoggerPort], None],
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    logger = logger_bootstrapper(pipeline, run_id, log_level)
    tracer = tracer_bootstrapper(settings)
    metrics = metrics_bootstrapper(settings)
    dq_monitor = dq_monitor_bootstrapper(settings, logger)

    bundle = ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    _log_observability_initialized(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )

    preflight_validator(tracer, metrics, settings.env, logger)

    return bundle


def _log_observability_initialized(
    *,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    dq_monitor: DQMonitorPort | None,
) -> None:
    """Emit structured bootstrap observability event."""
    logger.info(
        "observability_initialized",
        extra={
            "stage": "bootstrap",
            "metrics_type": type(metrics).__name__,
            "tracer_type": type(tracer).__name__,
            "dq_monitor_enabled": dq_monitor is not None,
        },
    )
