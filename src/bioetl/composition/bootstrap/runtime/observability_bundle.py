"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._observability_bundle_support import (
    build_observability_components as _build_observability_components,
    resolve_observability_bootstrappers as _resolve_observability_bootstrappers,
    validate_observability_preflight_impl,
)
from bioetl.composition.bootstrap.runtime.observability_assembly import (
    create_observability_bundle as _create_observability_bundle,
    log_observability_initialized as _log_observability_initialized,
    run_observability_preflight as _run_observability_preflight,
    settings_control_plane as _settings_control_plane,
)
from bioetl.composition.observability import (
    ObservabilityBundle,
)
from bioetl.domain.ports import (
    AuditPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from bioetl.domain.ports import DQMonitorPort
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "bootstrap_observability_bundle_impl",
    "validate_observability_preflight_impl",
]

def bootstrap_observability_bundle_impl(
    *,
    pipeline: str,
    run_id: UUID,
    settings: Settings,
    log_level: str,
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort] | None = None,
    tracer_bootstrapper: Callable[[Settings], TracingPort] | None = None,
    metrics_bootstrapper: Callable[[Settings], MetricsPort] | None = None,
    audit_bootstrapper: Callable[
        [Settings, LoggerPort, MetricsPort, TracingPort], AuditPort
    ]
    | None = None,
    dq_monitor_bootstrapper: Callable[
        [Settings, LoggerPort | None], DQMonitorPort | None
    ]
    | None = None,
    preflight_validator: Callable[
        ...,
        None,
    ]
    | None = None,
    yaml_config: object | None = None,
    skip_gold: bool = False,
) -> ObservabilityBundle:
    """Build validated logger/metrics/tracer/DQ-monitor bundle for a pipeline run.

    Creates each observability component via the provided bootstrapper callables,
    logs initialization details, and runs preflight validation.

    Bootstrappers receive the run context and settings declared by the signature.
    Args:
        tracer_bootstrapper: Callable that creates a TracingPort from settings.
        metrics_bootstrapper: Callable that creates a MetricsPort from settings.
        dq_monitor_bootstrapper: Callable that creates an optional DQMonitorPort
            from settings and logger.
        preflight_validator: Callable that validates the assembled components and
            emits warnings for production misconfigurations.

    Returns:
        Validated ObservabilityBundle with logger, metrics, tracer, and DQ monitor.
    """
    bootstrappers = _resolve_observability_bootstrappers(
        logger_bootstrapper=logger_bootstrapper,
        tracer_bootstrapper=tracer_bootstrapper,
        metrics_bootstrapper=metrics_bootstrapper,
        audit_bootstrapper=audit_bootstrapper,
        dq_monitor_bootstrapper=dq_monitor_bootstrapper,
        preflight_validator=preflight_validator,
    )

    components = _build_observability_components(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=bootstrappers.logger,
        tracer_bootstrapper=bootstrappers.tracer,
        metrics_bootstrapper=bootstrappers.metrics,
        audit_bootstrapper=bootstrappers.audit,
        dq_monitor_bootstrapper=bootstrappers.dq_monitor,
    )

    bundle = _create_observability_bundle(components)
    control_plane = _settings_control_plane(settings)

    _run_observability_preflight(
        components=components,
        settings=settings,
        preflight_validator=bootstrappers.preflight,
        control_plane=control_plane,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )

    _log_observability_initialized(
        components=components,
        control_plane=control_plane,
    )

    return bundle
