"""Bootstrap functions for runtime observability components."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol, cast
from uuid import UUID

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import (
    AuditPort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.infrastructure.observability import (
    OpenTelemetryTracer,
    PrometheusMetrics,
    UnifiedLogger,
)
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

from .dq_bootstrap import bootstrap_dq_monitor_port as _bootstrap_dq_monitor_port_impl
from .logger_bootstrap import bootstrap_logger_port as _bootstrap_logger_port_impl
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
from .tracing_bootstrap import bootstrap_tracer_port as _bootstrap_tracer_port_impl

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings

__all__ = [
    "MetricsServerError",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_observability_bundle",
    "bootstrap_tracer_port",
    "maybe_start_metrics_server",
    "validate_observability_preflight",
]


class _ObservabilityApiModule(Protocol):
    """Typed subset of the public observability API used by this module."""

    def start_metrics_server(
        self,
        port: int = 8000,
        addr: str = "0.0.0.0",
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        logger: LoggerPort | None = None,
    ) -> bool:
        """Start the public metrics server."""
        ...


def _create_runtime_audit_port(
    *,
    settings: Settings,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
) -> AuditPort:
    """Resolve the canonical runtime audit factory lazily.

    Importing the broader ``bioetl.composition.factories`` package at module load
    time can pull in unrelated assembly surfaces. Keep the audit factory import
    at bootstrap time so runtime observability stays a thin entrypoint.
    """
    from bioetl.composition.factories.storage.audit import (
        create_audit_port as create_audit_port_impl,
    )

    return create_audit_port_impl(
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
    )


def validate_observability_preflight(
    tracer: TracingPort,
    metrics: MetricsPort,
    environment: str,
    logger: LoggerPort,
    allow_noop_in_prod: bool = False,
    *,
    audit: AuditPort | None = None,
    audit_required: bool = False,
    control_plane: object | None = None,
    yaml_config: object | None = None,
    skip_gold: bool = False,
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
        allow_noop_in_prod=allow_noop_in_prod,
        audit=audit,
        audit_required=audit_required,
        control_plane=control_plane,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
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
    )


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Compatibility patch-point delegating to the composition observability seam."""
    observability_api = cast(
        _ObservabilityApiModule,
        import_module("bioetl.composition.observability_api"),
    )
    return observability_api.start_metrics_server(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


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
        monitor_factory=DataQualityMonitorService,
        noop_logger_factory=NoOpLogger,
    )


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
    yaml_config: object | None = None,
    skip_gold: bool = False,
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
        audit_bootstrapper=lambda audit_settings,
        audit_logger,
        audit_metrics,
        audit_tracer: (
            _create_runtime_audit_port(
                settings=audit_settings,
                logger=audit_logger,
                metrics=audit_metrics,
                tracing=audit_tracer,
            )
        ),
        dq_monitor_bootstrapper=bootstrap_dq_monitor_port,
        preflight_validator=validate_observability_preflight,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )
