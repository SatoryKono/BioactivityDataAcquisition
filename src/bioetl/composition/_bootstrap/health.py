"""Bootstrap functions for health service.

Contains bootstrap functions for HealthService and HealthServer.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.data_source_factory import DataSourceFactory
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.services import HealthService
    from bioetl.interfaces.http.health_server import HealthServer

__all__ = [
    "bootstrap_health_server",
    "bootstrap_health_service",
]


def bootstrap_health_service() -> HealthService:
    """Bootstrap HealthService for CLI health operations.

    Creates a HealthService for checking provider health.
    Wires up DataSourceFactory for adapter creation.

    Returns:
        HealthService configured for CLI operations.

    Example:
        >>> service = bootstrap_health_service()
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
    """
    from bioetl.application.services import HealthService

    noop_logger = NoOpLogger()

    return HealthService(
        logger=noop_logger,
        _factory=DataSourceFactory,
    )


def bootstrap_health_server(
    host: str = "0.0.0.0",
    port: int = 8080,
) -> HealthServer:
    """Bootstrap HealthServer with all dependencies via DI.

    Creates HealthServer with properly injected:
    - PrometheusMetrics for observability
    - ProviderHealthMonitor for health state tracking

    This is the composition root for the health server CLI command,
    ensuring all dependencies are created in the composition layer.

    Args:
        host: Host to bind to (default: "0.0.0.0").
        port: Port to listen on (default: 8080).

    Returns:
        HealthServer configured with injected dependencies.

    Example:
        >>> server = bootstrap_health_server(host="127.0.0.1", port=9090)
        >>> await server.start()
        >>> # ... server running ...
        >>> await server.stop()
    """
    from bioetl.infrastructure.adapters.http.health_monitor import (
        ProviderHealthMonitor,
    )
    from bioetl.infrastructure.observability.prometheus_metrics import (
        PrometheusMetrics,
    )
    from bioetl.interfaces.http.health_server import HealthServer

    # Create metrics port for health monitor
    metrics = PrometheusMetrics()

    # Create health monitor with injected metrics
    health_monitor = ProviderHealthMonitor(metrics=metrics)

    # Create and return server with injected dependencies
    return HealthServer(
        host=host,
        port=port,
        health_monitor=health_monitor,
    )
