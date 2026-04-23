"""Runtime observability bundle assembly helpers."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.bootstrap.runtime.dq_bootstrap import (
    bootstrap_dq_monitor_port as _bootstrap_dq_monitor_port_impl,
)
from bioetl.composition.bootstrap.runtime.metrics_bootstrap import (
    bootstrap_metrics_port as _bootstrap_metrics_port_impl,
)
from bioetl.composition.bootstrap.runtime.observability_bundle import (
    bootstrap_observability_bundle_impl,
    validate_observability_preflight_impl,
)
from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
    bootstrap_tracer_port as _bootstrap_tracer_port_impl,
)
from bioetl.composition.factories.storage.audit import create_audit_port
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.observability_resolution import (
    resolve_metrics_port,
    resolve_tracing_port,
)
from bioetl.domain.ports import (
    AuditPort,
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

__all__ = ["build_observability_bundle"]


def _build_logger_bootstrapper(
    logger_factory: Callable[..., LoggerPort],
) -> Callable[[str, RunID, str], LoggerPort]:
    """Build logger bootstrapper closure for canonical observability bundle."""

    def bootstrap_logger(
        logger_pipeline: str,
        logger_run_id: RunID,
        logger_level: str,
    ) -> LoggerPort:
        return logger_factory(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        )

    return bootstrap_logger


def _resolve_tracer_port(
    *,
    tracer_settings: Settings,
    tracer_factory: Callable[[str], TracingPort] | None,
    noop_tracing_factory: Callable[[], TracingPort] | None,
) -> TracingPort:
    """Resolve tracing port using explicit factories or canonical fallbacks."""
    if tracer_factory is None and noop_tracing_factory is None:
        return _bootstrap_tracer_port_impl(
            settings=tracer_settings,
            service_name="bioetl",
        )
    if tracer_settings.observability.tracing_enabled and tracer_factory is not None:
        return tracer_factory("bioetl")
    if noop_tracing_factory is not None:
        return noop_tracing_factory()
    return resolve_tracing_port(tracer=None, settings=tracer_settings)


def _build_tracer_bootstrapper(
    *,
    tracer_factory: Callable[[str], TracingPort] | None,
    noop_tracing_factory: Callable[[], TracingPort] | None,
) -> Callable[[Settings], TracingPort]:
    """Build tracer bootstrapper closure for canonical observability bundle."""

    def bootstrap_tracer(tracer_settings: Settings) -> TracingPort:
        return _resolve_tracer_port(
            tracer_settings=tracer_settings,
            tracer_factory=tracer_factory,
            noop_tracing_factory=noop_tracing_factory,
        )

    return bootstrap_tracer


def _resolve_metrics_port(
    *,
    metrics_settings: Settings,
    metrics_factory: Callable[[], MetricsPort] | None,
    noop_metrics_factory: Callable[..., MetricsPort] | None,
) -> MetricsPort:
    """Resolve metrics port using explicit factories or canonical fallbacks."""
    if metrics_factory is None and noop_metrics_factory is None:
        return _bootstrap_metrics_port_impl(
            settings=metrics_settings,
        )
    if metrics_settings.observability.metrics_enabled and metrics_factory is not None:
        return metrics_factory()
    if noop_metrics_factory is not None:
        return noop_metrics_factory(warn_on_use=False)
    return resolve_metrics_port(metrics=None, settings=metrics_settings)


def _build_metrics_bootstrapper(
    *,
    metrics_factory: Callable[[], MetricsPort] | None,
    noop_metrics_factory: Callable[..., MetricsPort] | None,
) -> Callable[[Settings], MetricsPort]:
    """Build metrics bootstrapper closure for canonical observability bundle."""

    def bootstrap_metrics(metrics_settings: Settings) -> MetricsPort:
        return _resolve_metrics_port(
            metrics_settings=metrics_settings,
            metrics_factory=metrics_factory,
            noop_metrics_factory=noop_metrics_factory,
        )

    return bootstrap_metrics


def _build_dq_monitor_bootstrapper(
    *,
    dq_monitor_factory: Callable[..., DQMonitorPort],
    noop_logger_factory: Callable[[], LoggerPort],
) -> Callable[[Settings, LoggerPort], DQMonitorPort]:
    """Build DQ monitor bootstrapper closure for canonical observability bundle."""

    def bootstrap_dq_monitor(
        dq_settings: Settings,
        dq_logger: LoggerPort,
    ) -> DQMonitorPort:
        return _bootstrap_dq_monitor_port_impl(
            settings=dq_settings,
            logger=dq_logger,
            monitor_factory=dq_monitor_factory,
            noop_logger_factory=noop_logger_factory,
        )

    return bootstrap_dq_monitor


def _build_audit_bootstrapper() -> Callable[
    [Settings, LoggerPort, MetricsPort, TracingPort], AuditPort
]:
    """Build audit bootstrapper closure for observability preflight wiring."""

    def bootstrap_audit(
        audit_settings: Settings,
        audit_logger: LoggerPort,
        audit_metrics: MetricsPort,
        audit_tracer: TracingPort,
    ) -> AuditPort:
        return create_audit_port(
            settings=audit_settings,
            logger=audit_logger,
            metrics=audit_metrics,
            tracing=audit_tracer,
        )

    return bootstrap_audit


def build_observability_bundle(
    *,
    pipeline: str,
    run_id: RunID,
    settings: Settings,
    log_level: str = "INFO",
    yaml_config: object | None = None,
    skip_gold: bool = False,
    logger_factory: Callable[..., LoggerPort] = UnifiedLogger,
    tracer_factory: Callable[[str], TracingPort] | None = None,
    metrics_factory: Callable[[], MetricsPort] | None = None,
    noop_tracing_factory: Callable[[], TracingPort] | None = None,
    noop_metrics_factory: Callable[..., MetricsPort] | None = None,
    dq_monitor_factory: Callable[..., DQMonitorPort] = DataQualityMonitorService,
    noop_logger_factory: Callable[[], LoggerPort] = NoOpLogger,
) -> ObservabilityBundle:
    """Build observability bundle via the canonical bootstrap implementation."""

    return bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=_build_logger_bootstrapper(logger_factory),
        tracer_bootstrapper=_build_tracer_bootstrapper(
            tracer_factory=tracer_factory,
            noop_tracing_factory=noop_tracing_factory,
        ),
        metrics_bootstrapper=_build_metrics_bootstrapper(
            metrics_factory=metrics_factory,
            noop_metrics_factory=noop_metrics_factory,
        ),
        audit_bootstrapper=_build_audit_bootstrapper(),
        dq_monitor_bootstrapper=_build_dq_monitor_bootstrapper(
            dq_monitor_factory=dq_monitor_factory,
            noop_logger_factory=noop_logger_factory,
        ),
        preflight_validator=validate_observability_preflight_impl,
        yaml_config=yaml_config,
        skip_gold=skip_gold,
    )
