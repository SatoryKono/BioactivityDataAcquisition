"""Bootstrap functions for health CLI operations.

Contains bootstrap functions for HealthService and health server dependencies.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.assembly.health_server import (
    HealthServerDependencies,
    create_health_server_dependencies,
)
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_checkpoint_adapter,
    bootstrap_quarantine_adapter,
)
from bioetl.composition.bootstrap.cli.noop import (
    create_noop_logger,
    create_noop_metrics,
    create_noop_tracing,
)
from bioetl.composition.bootstrap.cli.service_builders import (
    build_cli_quarantine_service,
)
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.services.ops.health_service import HealthService
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "HealthServerDependencies",
    "bootstrap_health_server_dependencies",
    "bootstrap_health_server_quarantine_service",
    "bootstrap_health_service",
]


def create_health_service(
    *,
    logger: LoggerPort,
    settings: Settings,
    metrics: MetricsPort | None = None,
) -> HealthService:
    """Delegate health-service assembly lazily to avoid server startup fan-out."""
    from bioetl.composition.bootstrap.assembly.health_service import (
        create_health_service as _create_health_service,
    )

    return _create_health_service(
        logger=logger,
        settings=settings,
        metrics=metrics,
    )


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


def bootstrap_health_server_quarantine_service(
    *,
    data_root: Path | None = None,
) -> QuarantineService:
    """Build quarantine explorer storage without manifest-service fan-out."""
    return build_cli_quarantine_service(
        settings=get_settings(),
        quarantine_port_factory=partial(
            bootstrap_quarantine_adapter,
            data_root=data_root,
        ),
        logger_factory=create_noop_logger,
        metrics_resolver=lambda **_: create_noop_metrics(),
        tracing_resolver=cast(
            "Callable[..., TracingPort]",
            lambda **_: create_noop_tracing(),
        ),
        run_manifest_service_factory=None,
        clock_factory=SystemClock,
    )


def bootstrap_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Bootstrap dependencies for HealthServer via DI.

    Creates and wires up:
    - PrometheusMetrics for observability
    - a read-only health monitor for provider status endpoints

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
        checkpoint_port_factory=partial(
            bootstrap_checkpoint_adapter,
            data_root=data_root,
        ),
        data_root=data_root,
    )
