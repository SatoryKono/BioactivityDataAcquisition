"""Sub-service for runtime observability bundle assembly."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability import OpenTelemetryTracer, PrometheusMetrics
from bioetl.infrastructure.observability.anomaly import DataQualityMonitorService
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
    dq_monitor_factory: Callable[
        ..., DataQualityMonitorService
    ] = DataQualityMonitorService,
) -> ObservabilityBundle:
    """Build observability bundle with optional DQ monitor wiring.

    Args:
        pipeline: Pipeline name used as a structured log field and tracer context.
        run_id: Run UUID for log correlation across all observability components.
        settings: Application settings driving feature flags for each component.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG'). Defaults to 'INFO'.
        logger_factory: Callable creating a LoggerPort from pipeline, run_id, and log_level.
        tracer_factory: Callable creating a TracingPort from a service name string.
        metrics_factory: Callable creating a MetricsPort (no arguments).
        noop_tracing_factory: Callable creating a NoOpTracing when tracing is disabled.
        noop_metrics_factory: Callable creating NoOpMetrics when metrics are disabled.
        dq_monitor_factory: Callable creating a DataQualityMonitorService when DQ monitoring
            is enabled.

    Returns:
        ObservabilityBundle with logger, metrics, tracer, and optional DQ monitor.
    """
    logger = logger_factory(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=True,
    )
    tracer: TracingPort = (
        tracer_factory("bioetl")
        if settings.observability.tracing_enabled
        else noop_tracing_factory()
    )
    metrics: MetricsPort = (
        metrics_factory()
        if settings.observability.metrics_enabled
        else noop_metrics_factory(warn_on_use=False)
    )

    dq_monitor = None
    if settings.observability.dq_monitor_enabled:
        dq_monitor = dq_monitor_factory(
            logger=logger,
            baseline_window=settings.observability.dq_baseline_window,
            z_score_threshold=settings.observability.dq_z_score_threshold,
        )
        dq_monitor.detector.min_baseline_samples = (
            settings.observability.dq_min_baseline_samples
        )
        dq_monitor.detector.set_threshold(
            "error_rate",
            min_value=0.0,
            max_value=settings.observability.dq_error_rate_max,
        )
        dq_monitor.detector.set_threshold(
            "quality_score",
            min_value=settings.observability.dq_quality_score_min,
            max_value=1.0,
        )

    return ObservabilityBundle(
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        dq_monitor=dq_monitor,
    )
