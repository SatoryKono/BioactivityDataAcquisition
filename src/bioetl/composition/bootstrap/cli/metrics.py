"""Bootstrap functions for metrics CLI operations.

Contains bootstrap functions for MetricsService.
Used for metrics server management from CLI (start, stop, status).

Note:
    This is for managing the metrics server, not for metrics collection.
    Runtime metrics collection uses bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.services.metrics_service import MetricsService

__all__ = ["bootstrap_metrics_service"]


def bootstrap_metrics_service() -> MetricsService:
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
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.infrastructure.observability.metrics_server_adapter import (
        MetricsServerAdapter,
    )

    logger = NoOpLogger()
    server = MetricsServerAdapter(logger=logger)

    return MetricsService(
        logger=logger,
        _server=server,
    )
