"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
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
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
    allow_noop_in_prod: bool = False,
) -> None:
    """Validate observability components for production readiness.

    Emits structured warnings when NoOp implementations are used in production.
    By default, production fails closed unless explicit override is enabled.

    Args:
        tracer: TracingPort to validate; warns if NoOpTracing in production.
        metrics: MetricsPort to validate; warns if NoOpMetrics in production.
        environment: Deployment environment name (e.g., 'prod', 'staging').
        logger: LoggerPort used to emit structured preflight warning events.
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
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpTracing is not allowed in prod. "
                "Enable tracing or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
            )

    if isinstance(metrics, NoOpMetrics):
        logger.warning(
            "noop_metrics_in_production",
            message="NoOpMetrics in production - metrics will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true "
            "to enable Prometheus metrics collection",
        )
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpMetrics is not allowed in prod. "
                "Enable metrics or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
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
    preflight_validator: Callable[
        [TracingPort, MetricsPort, str, LoggerPort, bool], None
    ],
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Creates each observability component via the provided bootstrapper callables,
    logs initialization details, and runs preflight validation.

    Args:
        pipeline: Pipeline name passed to the logger bootstrapper for context.
        run_id: Run UUID used for log correlation across all components.
        settings: Application settings forwarded to tracer, metrics, and DQ bootstrappers.
        log_level: Minimum log level string forwarded to the logger bootstrapper.
        logger_bootstrapper: Callable that creates a LoggerPort from pipeline, run_id,
            and log_level.
        tracer_bootstrapper: Callable that creates a TracingPort from settings.
        metrics_bootstrapper: Callable that creates a MetricsPort from settings.
        dq_monitor_bootstrapper: Callable that creates an optional DQMonitorPort
            from settings and logger.
        preflight_validator: Callable that validates the assembled components and
            emits warnings for production misconfigurations.

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

    preflight_validator(
        tracer,
        metrics,
        settings.env,
        logger,
        settings.observability.allow_noop_observability_in_prod,
    )

    return bundle


def _log_observability_initialized(
    *,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    dq_monitor: DQMonitorPort | None,
) -> None:
    """Emit structured bootstrap observability event.

    Args:
        logger: LoggerPort used to emit the initialization event.
        metrics: MetricsPort whose type name is included in the event.
        tracer: TracingPort whose type name is included in the event.
        dq_monitor: Optional DQ monitor; presence is recorded in the event.
    """
    logger.info(
        "observability_initialized",
        stage="bootstrap",
        metrics_type=type(metrics).__name__,
        tracer_type=type(tracer).__name__,
        dq_monitor_enabled=dq_monitor is not None,
    )
