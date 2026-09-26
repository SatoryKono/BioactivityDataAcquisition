"""Bootstrap functions for metrics CLI operations.

Contains bootstrap functions for MetricsService.
Used for metrics server management from CLI (start, stop, status).

Note:
    This is for managing the metrics server, not for metrics collection.
    Runtime metrics collection uses bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.observability.control_plane_integrity_metrics import (
    ControlPlaneIntegrityMetricsService,
)
from bioetl.application.services.ops.metrics_service import MetricsService
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.infrastructure.observability.metrics_publisher_adapter import (
    MetricsPublisherAdapter,
)
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time import SystemClock
from bioetl.composition.runtime_builders import control_plane_root
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.exceptions import BioETLError
from bioetl.infrastructure.control_plane import (
    FileRunLedgerStore,
    FileRunManifestStore,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = ["bootstrap_metrics_service", "create_metrics_service"]


def create_metrics_service(
    *,
    logger: LoggerPort | None = None,
    tracer: TracingPort | None = None,
) -> MetricsService:
    """Build a metrics service with a composition-owned server adapter."""
    resolved_logger = logger if logger is not None else NoOpLogger()
    return MetricsService(
        logger=resolved_logger,
        clock=SystemClock(),
        tracer=tracer,
        _server=MetricsServerAdapter(logger=resolved_logger),
        _publisher=MetricsPublisherAdapter(logger=resolved_logger),
    )


def refresh_control_plane_integrity_metrics(
    settings: Settings, *, logger: LoggerPort | None = None
) -> None:
    """Measure persisted manifest/ledger integrity before a terminal snapshot."""
    try:
        if not settings.observability.metrics_enabled:
            return
        ControlPlaneIntegrityMetricsService(
            manifest_port=FileRunManifestStore(
                base_path=control_plane_root(settings, "run_manifest")
            ),
            ledger_port=FileRunLedgerStore(
                base_path=control_plane_root(settings, "run_ledger")
            ),
            metrics=PrometheusMetrics(),
        ).refresh()
    except (
        BioETLError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        if logger is not None:
            logger.warning(
                "integrity_metrics_refresh_failed", error_type=type(exc).__name__
            )


def bootstrap_metrics_service(
    *,
    logger: LoggerPort | None = None,
) -> MetricsService:
    """Bootstrap metrics service for administrative operations.

    Creates a MetricsService with infrastructure dependencies injected.
    Used by CLI and other interfaces for metrics server management.

    Returns:
        MetricsService instance ready for use.

    Example:
        >>> service = bootstrap_metrics_service()
        >>> result = service.start(port=8000)
        >>> # result.success is True if server started
    """
    settings = get_settings()
    tracer = resolve_tracing_port(
        tracer=None,
        settings=settings,
        service_name="bioetl.metrics_admin",
    )
    return create_metrics_service(logger=logger, tracer=tracer)
