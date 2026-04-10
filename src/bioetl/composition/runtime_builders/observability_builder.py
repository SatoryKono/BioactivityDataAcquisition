"""Compatibility wrapper for canonical runtime observability assembly."""

from __future__ import annotations

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
from bioetl.domain.ports import DQMonitorPort, LoggerPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import Settings
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
) -> ObservabilityBundle:
    """Build observability bundle via the canonical bootstrap implementation."""

    return bootstrap_observability_bundle_impl(
        pipeline=pipeline,
        run_id=run_id,
        settings=settings,
        log_level=log_level,
        logger_bootstrapper=lambda logger_pipeline, logger_run_id, logger_level: UnifiedLogger(
            pipeline=logger_pipeline,
            run_id=logger_run_id,
            log_level=logger_level,
            json_format=True,
        ),
        tracer_bootstrapper=lambda tracer_settings: _bootstrap_tracer_port_impl(
            settings=tracer_settings,
            service_name="bioetl",
        ),
        metrics_bootstrapper=lambda metrics_settings: _bootstrap_metrics_port_impl(
            settings=metrics_settings,
        ),
        dq_monitor_bootstrapper=lambda dq_settings, dq_logger: _bootstrap_dq_monitor_port_impl(
            settings=dq_settings,
            logger=dq_logger,
            monitor_factory=DataQualityMonitorService,
            noop_logger_factory=NoOpLogger,
        ),
        preflight_validator=validate_observability_preflight_impl,
    )
