"""Bootstrap functions for health CLI operations.

Contains bootstrap functions for HealthService and health server dependencies.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.assembly.health_service import (
    HealthServerDependencies,
    create_health_server_dependencies,
    create_health_service,
)
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.bootstrap.cli.run_manifest import (
    bootstrap_run_manifest_service,
)
from bioetl.composition.runtime_builders.config_access import get_settings

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService

__all__ = [
    "HealthServerDependencies",
    "bootstrap_health_server_dependencies",
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
    noop_logger = create_noop_logger()
    settings = get_settings()
    return create_health_service(
        logger=noop_logger,
        settings=settings,
    )


def bootstrap_health_server_dependencies() -> HealthServerDependencies:
    """Bootstrap dependencies for HealthServer via DI.

    Creates and wires up:
    - PrometheusMetrics for observability
    - ProviderHealthMonitor for health state tracking

    The actual HealthServer is created in the interfaces layer
    to maintain proper layer separation (composition cannot import interfaces).

    Returns:
        HealthServerDependencies with metrics, health_monitor, and a read-only
        control-plane run-manifest catalog.

    Example:
        >>> deps = bootstrap_health_server_dependencies()
        >>> server = HealthServer(host="127.0.0.1", port=9090,
        ...                       health_monitor=deps.health_monitor)
    """
    return create_health_server_dependencies(
        run_manifest_service_factory=bootstrap_run_manifest_service,
    )
