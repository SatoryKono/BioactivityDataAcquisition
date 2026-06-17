"""Bootstrap functions for runtime observability components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
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

from .dq_bootstrap import bootstrap_dq_monitor as _bootstrap_dq_monitor_impl
from .logger_bootstrap import bootstrap_logger as _bootstrap_logger_impl
from .metrics_bootstrap import bootstrap_metrics as _bootstrap_metrics_impl
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

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "MetricsServerError",
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability_bundle",
    "bootstrap_tracer",
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
    """Resolve the canonical runtime audit factory lazily."""
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
    """Validate observability components for production readiness."""
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


def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution."""
    return _bootstrap_logger_impl(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
    )


def bootstrap_tracer(
    settings: Settings,
    service_name: str = "bioetl",
) -> TracingPort:
    """Create a tracing port implementation for distributed tracing."""
    return _bootstrap_tracer_impl(
        settings=settings,
        service_name=service_name,
    )


def bootstrap_metrics(settings: Settings) -> MetricsPort:
    """Create a metrics port implementation."""
    return _bootstrap_metrics_impl(
        settings=settings,
    )


def maybe_start_metrics_server(settings: Settings) -> bool:
    """Start metrics server if enabled in settings."""
    return _maybe_start_metrics_server_impl(
        settings=settings,
    )


def bootstrap_dq_monitor(
    settings: Settings,
    logger: LoggerPort | None = None,
) -> DQMonitorPort | None:
    """Create a data quality monitor port implementation."""
    return _bootstrap_dq_monitor_impl(
        settings=settings,
        logger=logger,
    )


def bootstrap_observability_bundle(
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str = "INFO",
    yaml_config: object | None = None,
    skip_gold: bool = False,
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run."""
    return _bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=bootstrap_logger,
        tracer_bootstrapper=bootstrap_tracer,
        metrics_bootstrapper=bootstrap_metrics,
        audit_bootstrapper=lambda audit_settings, audit_logger, audit_metrics, audit_tracer: (
            _create_runtime_audit_port(
                settings=audit_settings,
                logger=audit_logger,
                metrics=audit_metrics,
                tracing=audit_tracer,
            )
        ),
        dq_monitor_bootstrapper=bootstrap_dq_monitor,
        preflight_validator=validate_observability_preflight,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )
