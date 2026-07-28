# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Support helpers for runtime observability bundle bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime._observability_preflight_support import (
    requires_forensic_grade_observability_evidence,
    validate_control_plane_readiness,
    validate_forensic_grade_observability_evidence,
    validate_prod_noop_components,
)
from bioetl.composition.bootstrap.runtime.observability_assembly import (
    control_plane_settings as _control_plane_settings,
    default_audit_bootstrapper as _default_audit_bootstrapper,
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
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "ObservabilityBootstrappers",
    "ObservabilityComponents",
    "build_observability_components",
    "resolve_observability_bootstrappers",
    "validate_observability_preflight_impl",
]


@dataclass(frozen=True, slots=True)
class ObservabilityComponents:
    logger: LoggerPort
    tracer: TracingPort
    metrics: MetricsPort
    audit: AuditPort
    dq_monitor: DQMonitorPort | None


# Backward-compatible private alias used by assembly/tests.
_ObservabilityComponents = ObservabilityComponents


def build_observability_components(
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
) -> ObservabilityComponents:
    """Construct the concrete observability collaborators for one run."""
    logger = logger_bootstrapper(pipeline, run_id, log_level)
    tracer = tracer_bootstrapper(settings)
    metrics = metrics_bootstrapper(settings)
    audit = (
        audit_bootstrapper(settings, logger, metrics, tracer)
        if audit_bootstrapper is not None
        else NoOpAudit()
    )
    return ObservabilityComponents(
        logger=logger,
        tracer=tracer,
        metrics=metrics,
        audit=audit,
        dq_monitor=dq_monitor_bootstrapper(settings, logger),
    )


# Backward-compatible private alias used by tests/patches.
_build_observability_components = build_observability_components


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


@dataclass(frozen=True, slots=True)
class ObservabilityBootstrappers:
    logger: Callable[[str, UUID, str], LoggerPort]
    tracer: Callable[[Settings], TracingPort]
    metrics: Callable[[Settings], MetricsPort]
    audit: Callable[[Settings, LoggerPort, MetricsPort, TracingPort], AuditPort]
    dq_monitor: Callable[[Settings, LoggerPort | None], DQMonitorPort | None]
    preflight: Callable[..., None]


_ObservabilityBootstrappers = ObservabilityBootstrappers


def resolve_observability_bootstrappers(
    *,
    logger_bootstrapper: Callable[[str, UUID, str], LoggerPort] | None,
    tracer_bootstrapper: Callable[[Settings], TracingPort] | None,
    metrics_bootstrapper: Callable[[Settings], MetricsPort] | None,
    audit_bootstrapper: (
        Callable[[Settings, LoggerPort, MetricsPort, TracingPort], AuditPort] | None
    ),
    dq_monitor_bootstrapper: (
        Callable[[Settings, LoggerPort | None], DQMonitorPort | None] | None
    ),
    preflight_validator: Callable[..., None] | None,
) -> ObservabilityBootstrappers:
    """Fill optional bootstrapper hooks with default composition collaborators."""
    resolved_logger: Callable[[str, UUID, str], LoggerPort]
    if logger_bootstrapper is None:
        from bioetl.composition.bootstrap.runtime.logger_bootstrap import (
            bootstrap_logger,
        )

        resolved_logger = bootstrap_logger
    else:
        resolved_logger = logger_bootstrapper

    resolved_tracer: Callable[[Settings], TracingPort]
    if tracer_bootstrapper is None:
        from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
            bootstrap_tracer,
        )

        resolved_tracer = bootstrap_tracer
    else:
        resolved_tracer = tracer_bootstrapper

    resolved_metrics: Callable[[Settings], MetricsPort]
    if metrics_bootstrapper is None:
        from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
            bootstrap_metrics,
        )

        resolved_metrics = bootstrap_metrics
    else:
        resolved_metrics = metrics_bootstrapper

    resolved_dq_monitor: Callable[[Settings, LoggerPort | None], DQMonitorPort | None]
    if dq_monitor_bootstrapper is None:
        from bioetl.composition.bootstrap.runtime.dq_bootstrap import (
            bootstrap_dq_monitor,
        )

        resolved_dq_monitor = bootstrap_dq_monitor
    else:
        resolved_dq_monitor = dq_monitor_bootstrapper

    return ObservabilityBootstrappers(
        logger=resolved_logger,
        tracer=resolved_tracer,
        metrics=resolved_metrics,
        audit=(
            _default_audit_bootstrapper
            if audit_bootstrapper is None
            else audit_bootstrapper
        ),
        dq_monitor=resolved_dq_monitor,
        preflight=(
            validate_observability_preflight_impl
            if preflight_validator is None
            else preflight_validator
        ),
    )


_resolve_observability_bootstrappers = resolve_observability_bootstrappers


def _audit_required(*, audit: AuditPort | None, audit_required: bool) -> bool:
    return audit_required and audit is not None and isinstance(audit, NoOpAudit)
