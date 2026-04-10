"""Compatibility wrapper for canonical runtime observability assembly."""

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
)
from bioetl.composition.bootstrap.runtime.observability_bundle import (
    validate_observability_preflight_impl,
)
from bioetl.composition.bootstrap.runtime.tracing_bootstrap import (
    bootstrap_tracer_port as _bootstrap_tracer_port_impl,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports import DQMonitorPort, LoggerPort, MetricsPort, TracingPort
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability import OpenTelemetryTracer, PrometheusMetrics
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

__all__ = ["build_observability_bundle"]


def build_observability_bundle(
    *,
    pipeline: str,
    run_id: RunID,
    settings: Settings,
    log_level: str = "INFO",
    logger_factory: Callable[..., LoggerPort] = UnifiedLogger,
    tracer_factory: Callable[[str], TracingPort] = OpenTelemetryTracer,
    metrics_factory: Callable[[], MetricsPort] = PrometheusMetrics,
    noop_tracing_factory: Callable[[], TracingPort] = NoOpTracing,
    noop_metrics_factory: Callable[..., MetricsPort] = NoOpMetrics,
    dq_monitor_factory: Callable[..., DQMonitorPort] = DataQualityMonitorService,
    noop_logger_factory: Callable[[], LoggerPort] = NoOpLogger,
) -> ObservabilityBundle:
    """Build observability bundle via the canonical bootstrap implementation."""

    return bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=lambda logger_pipeline, logger_run_id, logger_level: logger_factory(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        ),
        tracer_bootstrapper=lambda tracer_settings: (
            _bootstrap_tracer_port_impl(
                settings=tracer_settings,
                service_name="bioetl",
            )
            if tracer_factory is OpenTelemetryTracer and noop_tracing_factory is NoOpTracing
            else (
                tracer_factory("bioetl")
                if tracer_settings.observability.tracing_enabled
                else noop_tracing_factory()
            )
        ),
        metrics_bootstrapper=lambda metrics_settings: (
            _bootstrap_metrics_port_impl(
                settings=metrics_settings,
            )
            if metrics_factory is PrometheusMetrics and noop_metrics_factory is NoOpMetrics
            else (
                metrics_factory()
                if metrics_settings.observability.metrics_enabled
                else noop_metrics_factory(warn_on_use=False)
            )
        ),
        dq_monitor_bootstrapper=lambda dq_settings, dq_logger: _bootstrap_dq_monitor_port_impl(
            settings=dq_settings,
            logger=dq_logger,
            monitor_factory=dq_monitor_factory,
            noop_logger_factory=noop_logger_factory,
        ),
        preflight_validator=validate_observability_preflight_impl,
    )
