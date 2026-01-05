"""Bootstrap functions for health service.

Contains bootstrap functions for HealthService.
Used primarily by CLI health operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.data_source_factory import DataSourceFactory
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.services import HealthService

__all__ = [
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
