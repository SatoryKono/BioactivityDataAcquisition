"""Extracted validate_observability_preflight for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from bioetl.domain.ports import (
    AuditPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

from .observability_bundle import (
    validate_observability_preflight_impl as _validate_observability_preflight_impl,
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
