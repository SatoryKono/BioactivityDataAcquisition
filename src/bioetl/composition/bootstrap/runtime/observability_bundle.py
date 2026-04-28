"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._observability_preflight_support import (
    requires_forensic_grade_observability_evidence,
    validate_control_plane_readiness,
    validate_forensic_grade_observability_evidence,
    validate_prod_noop_components,
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
from bioetl.domain.ports.noop import NoOpAudit

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
    *,
    audit: AuditPort | None = None,
    audit_required: bool = False,
    control_plane: object | None = None,
    yaml_config: object | None = None,
    skip_gold: bool = False,
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
    required_profile = _control_plane_settings(control_plane=control_plane)[0]
    forensic_grade_required = requires_forensic_grade_observability_evidence(
        required_persistence_profile=required_profile,
    )
    if environment != "prod" and not forensic_grade_required:
        return
    if environment == "prod":
        validate_prod_noop_components(
            tracer=tracer,
            metrics=metrics,
            logger=logger,
            allow_noop_in_prod=allow_noop_in_prod,
            audit=audit,
            audit_required=audit_required,
            audit_required_fn=_audit_required,
        )
    if forensic_grade_required:
        validate_forensic_grade_observability_evidence(
            tracer=tracer,
            metrics=metrics,
            logger=logger,
            audit=audit,
        )
    validate_control_plane_readiness(
        logger=logger,
        control_plane=control_plane,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
        control_plane_settings_fn=_control_plane_settings,
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
    audit_bootstrapper: Callable[
        [Settings, LoggerPort, MetricsPort, TracingPort], AuditPort
    ]
    | None,
    dq_monitor_bootstrapper: Callable[
        [Settings, LoggerPort | None], DQMonitorPort | None
    ],
    preflight_validator: Callable[
        ...,
        None,
    ],
    yaml_config: object | None = None,
    skip_gold: bool = False,
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
    audit = (
        audit_bootstrapper(settings, logger, metrics, tracer)
        if audit_bootstrapper is not None
        else NoOpAudit()
    )
    dq_monitor = dq_monitor_bootstrapper(settings, logger)

    bundle = ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        audit=audit,
        dq_monitor=dq_monitor,
    )

    preflight_validator(
        tracer=tracer,
        metrics=metrics,
        environment=settings.env,
        logger=logger,
        allow_noop_in_prod=settings.observability.allow_noop_observability_in_prod,
        audit=audit,
        audit_required=bool(getattr(settings.observability, "audit_enabled", False)),
        control_plane=getattr(
            getattr(settings, "pipeline", None), "control_plane", None
        ),
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )

    _log_observability_initialized(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        audit=audit,
        dq_monitor=dq_monitor,
        control_plane=getattr(
            getattr(settings, "pipeline", None), "control_plane", None
        ),
    )

    return bundle


def _log_observability_initialized(
    *,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
    audit: AuditPort,
    dq_monitor: DQMonitorPort | None,
    control_plane: object | None,
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
        logger_type=type(logger).__name__,
        metrics_type=type(metrics).__name__,
        tracer_type=type(tracer).__name__,
        audit_type=type(audit).__name__,
        audit_enabled=not isinstance(audit, NoOpAudit),
        dq_monitor_enabled=dq_monitor is not None,
        required_persistence_profile=_control_plane_settings(
            control_plane=control_plane
        )[0],
        run_manifest_enabled=_control_plane_settings(control_plane=control_plane)[1],
        run_ledger_enabled=_control_plane_settings(control_plane=control_plane)[2],
        preflight_status="passed",
    )


def _audit_required(*, audit: AuditPort | None, audit_required: bool) -> bool:
    return audit_required and audit is not None and isinstance(audit, NoOpAudit)


def _control_plane_settings(*, control_plane: object | None) -> tuple[str, bool, bool]:
    required_profile = str(
        getattr(
            control_plane,
            "required_persistence_profile",
            "degraded_observable",
        )
        or "degraded_observable"
    )
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    return required_profile, manifest_enabled, ledger_enabled
