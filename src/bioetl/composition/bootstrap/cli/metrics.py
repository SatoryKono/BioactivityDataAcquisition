"""Bootstrap functions for metrics CLI operations.

Contains bootstrap functions for MetricsService.
Used for metrics server management from CLI (start, stop, status).

Note:
    This is for managing the metrics server, not for metrics collection.
    Runtime metrics collection uses bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.metrics_service import MetricsService
from bioetl.composition.bootstrap.assembly.metrics_service import (
    create_metrics_service,
)
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.composition.runtime_builders.config_access import get_settings

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

__all__ = ["bootstrap_metrics_service"]


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
