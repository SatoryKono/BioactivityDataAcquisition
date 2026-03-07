"""Bootstrap functions for runtime observability components."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
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

from .dq_bootstrap import bootstrap_dq_monitor as _bootstrap_dq_monitor_impl
from .dq_bootstrap import bootstrap_dq_monitor_port as _bootstrap_dq_monitor_port_impl
from .logger_bootstrap import bootstrap_logger as _bootstrap_logger_impl
from .logger_bootstrap import bootstrap_logger_port as _bootstrap_logger_port_impl
from .metrics_bootstrap import bootstrap_metrics as _bootstrap_metrics_impl
from .metrics_bootstrap import bootstrap_metrics_port as _bootstrap_metrics_port_impl
from .metrics_bootstrap import (
    maybe_start_metrics_server as _maybe_start_metrics_server_impl,
)
from .observability_bundle import (
    bootstrap_observability_bundle_impl as _bootstrap_observability_bundle_impl,
)
from .observability_bundle import (
    validate_observability_preflight_impl as _validate_observability_preflight_impl,
)
from .tracing_bootstrap import bootstrap_tracer as _bootstrap_tracer_impl
from .tracing_bootstrap import bootstrap_tracer_port as _bootstrap_tracer_port_impl

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

    Args:
        tracer: TracingPort to validate; checked for NoOp in production.
        metrics: MetricsPort to validate; checked for NoOp in production.
        environment: Deployment environment name (e.g., 'prod', 'staging').
        logger: LoggerPort used to emit preflight validation warnings.
    """
    _validate_observability_preflight_impl(
        tracer=tracer,
        metrics=metrics,
        environment=environment,
        logger=logger,
    )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Args:
        pipeline: Pipeline name used as a structured log field.
        run_id: Run UUID for log correlation; a new UUID is generated if None.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Configured LoggerPort for structured pipeline logging.
    """

    def _logger_factory(
        logger_pipeline: str,
        logger_run_id: UUID,
        logger_level: str,
    ) -> LoggerPort:
        return UnifiedLogger(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        )

    return _bootstrap_logger_port_impl(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        logger_factory=_logger_factory,
    )


def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Deprecated alias for :func:`bootstrap_logger_port`.

    Args:
        pipeline: Pipeline name used as a structured log field.
        run_id: Run UUID for log correlation; a new UUID is generated if None.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Configured LoggerPort for structured pipeline logging.
    """
    return _bootstrap_logger_impl(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        logger_factory=lambda logger_pipeline, logger_run_id, logger_level: (
            UnifiedLogger(
                pipeline=logger_pipeline,
                run_id=logger_run_id,
                log_level=logger_level,
                json_format=True,
            )
        ),
    )


def bootstrap_tracer_port(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing.

    Args:
        settings: Application settings used to check whether tracing is enabled.
        service_name: OpenTelemetry service name for span identification.
            Defaults to 'bioetl'.

    Returns:
        Configured TracingPort for distributed tracing.
    """
    return _bootstrap_tracer_port_impl(
        settings=settings,
        service_name=service_name,
        tracer_factory=lambda trace_service_name: OpenTelemetryTracer(
            service_name=trace_service_name
        ),
    )


def bootstrap_tracer(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Deprecated alias for :func:`bootstrap_tracer_port`.

    Args:
        settings: Application settings used to check whether tracing is enabled.
        service_name: OpenTelemetry service name for span identification.

    Returns:
        Configured TracingPort for distributed tracing.
    """
    return _bootstrap_tracer_impl(
        settings=settings,
        service_name=service_name,
        tracer_factory=lambda trace_service_name: OpenTelemetryTracer(
            service_name=trace_service_name
        ),
    )


def bootstrap_metrics_port(settings: Settings) -> MetricsPort:
    """Create a metrics port implementation.

    Args:
        settings: Application settings used to determine if metrics are enabled.

    Returns:
        Configured MetricsPort for pipeline metrics collection.
    """
    return _bootstrap_metrics_port_impl(
        settings=settings,
        metrics_factory=PrometheusMetrics,
    )


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Start metrics server if enabled in settings.

    Args:
        settings: Application settings providing metrics port, address, and feature flags.

    Returns:
        True if the metrics server was started, False otherwise.
    """
    return _maybe_start_metrics_server_impl(
        settings=settings,
        start_server=start_metrics_server,
    )


def bootstrap_metrics(settings: Settings) -> MetricsPort:
    """Deprecated alias for :func:`bootstrap_metrics_port`.

    Args:
        settings: Application settings used to determine if metrics are enabled.

    Returns:
        Configured MetricsPort for pipeline metrics collection.
    """
    return _bootstrap_metrics_impl(settings=settings, metrics_factory=PrometheusMetrics)


def bootstrap_dq_monitor_port(
    settings: Settings,
    logger: LoggerPort | None = None,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation.

    Args:
        settings: Application settings used to check whether DQ monitoring is enabled.
        logger: Optional LoggerPort for structured DQ monitor logging; uses NoOpLogger
            if None.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    return _bootstrap_dq_monitor_port_impl(
        settings=settings,
        logger=logger,
        monitor_cls=DataQualityMonitor,
        noop_logger_cls=NoOpLogger,
    )


def bootstrap_dq_monitor(
    settings: Settings,
    logger: LoggerPort | None = None,
) -> DQMonitorPort | None:
    """Deprecated alias for :func:`bootstrap_dq_monitor_port`.

    Args:
        settings: Application settings used to check whether DQ monitoring is enabled.
        logger: Optional LoggerPort for structured DQ monitor logging.

    Returns:
        DQMonitorPort if DQ monitoring is enabled, None otherwise.
    """
    return _bootstrap_dq_monitor_impl(
        settings=settings,
        logger=logger,
        monitor_cls=DataQualityMonitor,
        noop_logger_cls=NoOpLogger,
    )


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Args:
        pipeline: Pipeline name used for logger and tracer context.
        run_id: Run UUID used for log correlation across all observability components.
        settings: Application settings driving feature flags for each component.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    return _bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=bootstrap_logger_port,
        tracer_bootstrapper=bootstrap_tracer_port,
        metrics_bootstrapper=bootstrap_metrics_port,
        dq_monitor_bootstrapper=bootstrap_dq_monitor_port,
        preflight_validator=validate_observability_preflight,
    )


def bootstrap_observability(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
) -> ObservabilityBundle:
    """Deprecated alias for :func:`bootstrap_observability_bundle`.

    Args:
        pipeline: Pipeline name used for logger and tracer context.
        run_id: Run UUID used for log correlation.
        settings: Application settings driving feature flags for each component.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    return bootstrap_observability_bundle(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
    )
