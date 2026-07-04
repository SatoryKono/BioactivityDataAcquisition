"""Assembly helpers for runtime observability bootstrap."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.composition.bootstrap.runtime.observability_bundle import (
        _ObservabilityComponents,
    )
    from bioetl.infrastructure.config.settings_api import Settings


def default_audit_bootstrapper(
    settings: Settings,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracer: TracingPort,
) -> AuditPort:
    """Create the canonical runtime audit port for observability bootstrap."""
    from bioetl.composition.factories.storage.audit import create_audit_port

    return create_audit_port(
        settings=settings,
        logger=logger,
        metrics=metrics,
        tracing=tracer,
    )


def create_observability_bundle(
    components: _ObservabilityComponents,
) -> ObservabilityBundle:
    """Create the public bundle object from resolved component ports."""
    return ObservabilityBundle(
        logger=components.logger,
        metrics=components.metrics,
        tracer=components.tracer,
        audit=components.audit,
        dq_monitor=components.dq_monitor,
    )


def log_observability_initialized(
    *,
    components: _ObservabilityComponents,
    control_plane: object | None,
) -> None:
    """Emit structured bootstrap observability event for one resolved bundle."""
    logger = components.logger
    metrics = components.metrics
    tracer = components.tracer
    audit = components.audit
    dq_monitor = components.dq_monitor
    logger.info(
        "observability_initialized",
        stage="bootstrap",
        logger_type=type(logger).__name__,
        metrics_type=type(metrics).__name__,
        tracer_type=type(tracer).__name__,
        audit_type=type(audit).__name__,
        audit_enabled=not isinstance(audit, NoOpAudit),
        dq_monitor_enabled=dq_monitor is not None,
        configured_required_persistence_profile=_control_plane_settings(
            control_plane=control_plane
        )[0],
        run_manifest_enabled=_control_plane_settings(control_plane=control_plane)[1],
        run_ledger_enabled=_control_plane_settings(control_plane=control_plane)[2],
        preflight_status="passed",
    )
    pipeline_name = getattr(logger, "pipeline", None)
    if not isinstance(pipeline_name, str) or not pipeline_name.strip():
        pipeline_name = "unknown"
    _set_component_runtime_gauge(
        metrics=metrics,
        pipeline_name=pipeline_name,
        component="logger",
        mode="noop" if logger.__class__.__name__ == "NoOpLogger" else "active",
    )
    _set_component_runtime_gauge(
        metrics=metrics,
        pipeline_name=pipeline_name,
        component="metrics",
        mode="noop" if isinstance(metrics, NoOpMetrics) else "active",
    )
    _set_component_runtime_gauge(
        metrics=metrics,
        pipeline_name=pipeline_name,
        component="tracing",
        mode="noop" if isinstance(tracer, NoOpTracing) else "active",
    )
    _set_component_runtime_gauge(
        metrics=metrics,
        pipeline_name=pipeline_name,
        component="audit",
        mode="noop" if isinstance(audit, NoOpAudit) else "active",
    )
    _set_component_runtime_gauge(
        metrics=metrics,
        pipeline_name=pipeline_name,
        component="dq_monitor",
        mode="disabled" if dq_monitor is None else "active",
    )


def _set_component_runtime_gauge(
    *,
    metrics: MetricsPort,
    pipeline_name: str,
    component: str,
    mode: str,
) -> None:
    """Emit one normalized component runtime-status gauge."""
    metrics.set_gauge(
        "bioetl_observability_runtime_status",
        1.0,
        {
            "pipeline": pipeline_name,
            "component": component,
            "mode": mode,
        },
    )


def _control_plane_settings(*, control_plane: object | None) -> tuple[str, bool, bool]:
    from bioetl.domain.control_plane.reproducibility_policy import (
        DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    )

    required_profile = str(
        getattr(
            control_plane,
            "required_persistence_profile",
            DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
        )
        or DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    manifest_enabled = bool(getattr(control_plane, "run_manifest_enabled", True))
    ledger_enabled = bool(getattr(control_plane, "run_ledger_enabled", True))
    return required_profile, manifest_enabled, ledger_enabled


# Public alias for bundle preflight helpers that share the assembly owner.
control_plane_settings = _control_plane_settings


def settings_control_plane(settings: Settings) -> object | None:
    pipeline_settings = getattr(settings, "pipeline", None)
    return getattr(pipeline_settings, "control_plane", None)


def run_observability_preflight(
    *,
    components: _ObservabilityComponents,
    settings: Settings,
    preflight_validator: Callable[..., None],
    control_plane: object | None,
    yaml_config: object | None,
    skip_gold: bool,
) -> None:
    """Validate observability readiness using one normalized control-plane view."""
    preflight_validator(
        tracer=components.tracer,
        metrics=components.metrics,
        environment=settings.env,
        logger=components.logger,
        allow_noop_in_prod=settings.observability.allow_noop_observability_in_prod,
        audit=components.audit,
        audit_required=bool(getattr(settings.observability, "audit_enabled", False)),
        control_plane=control_plane,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )
