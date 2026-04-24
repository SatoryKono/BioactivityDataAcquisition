"""Internal helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability import (
    ObservabilityBundle,
    ObservabilityContractError,
)
from bioetl.composition.runtime_builders.runner_builder_support import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.domain.ports import (
    AuditPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

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
    if environment != "prod":
        return

    if isinstance(logger, NoOpLogger):
        logger.warning(
            "noop_logger_in_production",
            stage="bootstrap",
            reason_code="noop_logger",
            message="NoOpLogger in production - structured runtime correlation will be lost",
            recommendation="Use UnifiedLogger or another structured LoggerPort implementation",
        )
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpLogger is not allowed in prod. "
                "Enable structured runtime logging or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
            )

    if isinstance(tracer, NoOpTracing):
        logger.warning(
            "noop_tracing_in_production",
            stage="bootstrap",
            reason_code="noop_tracing",
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
            stage="bootstrap",
            reason_code="noop_metrics",
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

    if _audit_required(audit=audit, audit_required=audit_required):
        logger.warning(
            "noop_audit_in_production",
            stage="bootstrap",
            reason_code="noop_audit",
            message="NoOpAudit in production - audit trail persistence will be lost",
            recommendation="Set BIOETL_OBSERVABILITY__AUDIT_ENABLED=true with a writable audit path",
        )
        if not allow_noop_in_prod:
            raise ObservabilityContractError(
                "NoOpAudit is not allowed in prod when audit logging is required. "
                "Enable audit or set "
                "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true "
                "for an explicit override."
            )

    required_profile, manifest_enabled, ledger_enabled = _control_plane_settings(
        control_plane=control_plane
    )
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    try:
        validate_required_persistence_profile(
            manifest_enabled=manifest_enabled,
            ledger_enabled=ledger_enabled,
            required_profile=required_profile,
            execution_label="Production observability preflight",
            missing_artifact_lineage_layers=missing_artifact_lineage_layers,
        )
    except RuntimeError as exc:
        logger.warning(
            "control_plane_readiness_preflight_failed",
            stage="bootstrap",
            reason_code="required_persistence_profile_unsatisfied",
            message=str(exc),
            required_persistence_profile=required_profile,
            run_manifest_enabled=manifest_enabled,
            run_ledger_enabled=ledger_enabled,
            missing_artifact_lineage_layers=list(missing_artifact_lineage_layers),
        )
        raise ObservabilityContractError(str(exc)) from exc


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
