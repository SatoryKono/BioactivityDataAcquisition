"""Shared helpers for production observability preflight validation."""

from __future__ import annotations

from typing import Protocol

from bioetl.composition.observability import ObservabilityContractError
from bioetl.composition.runtime_builders.runner_control_plane_assembly import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

class _AuditRequiredFn(Protocol):
    def __call__(self, *, audit: AuditPort | None, audit_required: bool) -> bool: ...

class _ControlPlaneSettingsFn(Protocol):
    def __call__(self, *, control_plane: object | None) -> tuple[str, bool, bool]: ...

_FORENSIC_GRADE_PROFILE = "forensic_grade"

def requires_forensic_grade_observability_evidence(
    *,
    required_persistence_profile: str,
) -> bool:
    """Return whether runtime preflight must fail closed for observability evidence."""
    return required_persistence_profile == _FORENSIC_GRADE_PROFILE

def _raise_if_noop_in_prod(
    *,
    condition: bool,
    logger: LoggerPort,
    allow_noop_in_prod: bool,
    event: str,
    reason_code: str,
    message: str,
    recommendation: str,
    error_message: str,
) -> None:
    """Log and raise for production no-op observability components."""
    if not condition:
        return
    logger.warning(
        event,
        stage="bootstrap",
        reason_code=reason_code,
        message=message,
        recommendation=recommendation,
    )
    if not allow_noop_in_prod:
        raise ObservabilityContractError(error_message)

def validate_prod_noop_components(
    *,
    tracer: TracingPort,
    metrics: MetricsPort,
    logger: LoggerPort,
    allow_noop_in_prod: bool,
    audit: AuditPort | None,
    audit_required: bool,
    audit_required_fn: _AuditRequiredFn,
) -> None:
    """Validate logger, tracer, metrics, and audit ports for prod readiness."""
    _raise_if_noop_in_prod(
        condition=isinstance(logger, NoOpLogger),
        logger=logger,
        allow_noop_in_prod=allow_noop_in_prod,
        event="noop_logger_in_production",
        reason_code="noop_logger",
        message="NoOpLogger in production - structured runtime correlation will be lost",
        recommendation="Use UnifiedLogger or another structured LoggerPort implementation",
        error_message=(
            "NoOpLogger is not allowed in prod. Enable structured runtime logging or "
            "set BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true for an "
            "explicit override."
        ),
    )
    _raise_if_noop_in_prod(
        condition=isinstance(tracer, NoOpTracing),
        logger=logger,
        allow_noop_in_prod=allow_noop_in_prod,
        event="noop_tracing_in_production",
        reason_code="noop_tracing",
        message="NoOpTracing in production - traces will be lost",
        recommendation=(
            "Set BIOETL_OBSERVABILITY__TRACING_ENABLED=true and configure "
            "OpenTelemetry endpoint"
        ),
        error_message=(
            "NoOpTracing is not allowed in prod. Enable tracing or set "
            "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true for an "
            "explicit override."
        ),
    )
    _raise_if_noop_in_prod(
        condition=isinstance(metrics, NoOpMetrics),
        logger=logger,
        allow_noop_in_prod=allow_noop_in_prod,
        event="noop_metrics_in_production",
        reason_code="noop_metrics",
        message="NoOpMetrics in production - metrics will be lost",
        recommendation=(
            "Set BIOETL_OBSERVABILITY__METRICS_ENABLED=true to enable Prometheus "
            "metrics collection"
        ),
        error_message=(
            "NoOpMetrics is not allowed in prod. Enable metrics or set "
            "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true for an "
            "explicit override."
        ),
    )
    _raise_if_noop_in_prod(
        condition=audit_required_fn(audit=audit, audit_required=audit_required),
        logger=logger,
        allow_noop_in_prod=allow_noop_in_prod,
        event="noop_audit_in_production",
        reason_code="noop_audit",
        message="NoOpAudit in production - audit trail persistence will be lost",
        recommendation=(
            "Set BIOETL_OBSERVABILITY__AUDIT_ENABLED=true with a writable audit path"
        ),
        error_message=(
            "NoOpAudit is not allowed in prod when audit logging is required. "
            "Enable audit or set "
            "BIOETL_OBSERVABILITY__ALLOW_NOOP_OBSERVABILITY_IN_PROD=true for an "
            "explicit override."
        ),
    )

def validate_forensic_grade_observability_evidence(
    *,
    tracer: TracingPort,
    metrics: MetricsPort,
    logger: LoggerPort,
    audit: AuditPort | None,
) -> None:
    """Fail closed when critical runs cannot produce forensic-grade evidence."""
    missing: list[str] = []
    if isinstance(logger, NoOpLogger):
        missing.append("structured_logger")
    if isinstance(tracer, NoOpTracing):
        missing.append("tracing")
    if isinstance(metrics, NoOpMetrics):
        missing.append("metrics")
    if audit is None or isinstance(audit, NoOpAudit):
        missing.append("audit")
    if not missing:
        return
    logger.warning(
        "forensic_grade_observability_evidence_unavailable",
        stage="bootstrap",
        reason_code="forensic_grade_observability_gap",
        message=(
            "forensic_grade runs require structured logger, tracing, metrics, "
            "and audit evidence before execution"
        ),
        missing_observability_evidence=missing,
        required_persistence_profile=_FORENSIC_GRADE_PROFILE,
    )
    joined = ", ".join(missing)
    raise ObservabilityContractError(
        "forensic_grade runs require non-noop observability evidence; missing: "
        f"{joined}"
    )

def validate_control_plane_readiness(
    *,
    logger: LoggerPort,
    control_plane: object | None,
    yaml_config: object | None,
    skip_gold: bool,
    control_plane_settings_fn: _ControlPlaneSettingsFn,
) -> None:
    """Validate control-plane persistence requirements for observability."""
    required_profile, manifest_enabled, ledger_enabled = control_plane_settings_fn(
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
