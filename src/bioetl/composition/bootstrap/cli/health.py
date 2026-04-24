"""Bootstrap functions for health CLI operations.

Contains bootstrap functions for HealthService and health server dependencies.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services import HealthService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.domain.ports import MetricsPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock

__all__ = [
    "HealthServerDependencies",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_service",
]


@dataclass(frozen=True, slots=True)
class HealthServerDependencies:
    """Dependencies for HealthServer, provided by composition layer.

    This dataclass allows composition to provide dependencies without
    importing from interfaces layer (which would violate layer rules).

    Attributes:
        health_monitor: ProviderHealthMonitor for health state tracking.
        metrics: MetricsPort for observability.
    """

    health_monitor: ProviderHealthMonitor
    metrics: MetricsPort


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

    return HealthService(
        logger=noop_logger,
        _factory=DataSourceFactory,
        clock=SystemClock(),
    )


def bootstrap_health_server_dependencies() -> HealthServerDependencies:
    """Bootstrap dependencies for HealthServer via DI.

    Creates and wires up:
    - PrometheusMetrics for observability
    - ProviderHealthMonitor for health state tracking

    The actual HealthServer is created in the interfaces layer
    to maintain proper layer separation (composition cannot import interfaces).

    Returns:
        HealthServerDependencies with metrics and health_monitor.

    Example:
        >>> deps = bootstrap_health_server_dependencies()
        >>> server = HealthServer(host="127.0.0.1", port=9090,
        ...                       health_monitor=deps.health_monitor)
    """
    # Create metrics port for health monitor
    metrics = PrometheusMetrics()

    # Create health monitor with injected metrics
    health_monitor = ProviderHealthMonitor(metrics=metrics)

    return HealthServerDependencies(
        health_monitor=health_monitor,
        metrics=metrics,
    )
