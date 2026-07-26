"""Canonical assembly helpers for health services and listener dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.health_service import HealthService
from bioetl.composition.bootstrap.assembly.health_server import (
    HealthServerDependencies,
    create_health_server_dependencies,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.composition.providers.registration import (
    resolve_provider_assembly_support,
)
from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "HealthServerDependencies",
    "create_health_server_dependencies",
    "create_health_service",
]


@dataclass(frozen=True, slots=True)
class _HealthCheckDataSourceFactory:
    """Composition-aware factory wrapper for CLI/server health probes."""

    logger: LoggerPort
    metrics: MetricsPort
    settings: Settings

    @staticmethod
    def list_providers() -> list[str]:
        return DataSourceFactory.list_providers()

    def create(self, provider: str) -> DataSourcePort:
        support = resolve_provider_assembly_support(None)
        http_client = support.create_http_client(
            provider,
            self.settings,
            metrics=self.metrics,
        )
        return DataSourceFactory.create(
            provider,
            http_client=http_client,
            logger=self.logger,
            settings=self.settings,
            metrics=self.metrics,
        )


def create_health_service(
    *,
    logger: LoggerPort,
    settings: Settings,
    metrics: MetricsPort | None = None,
) -> HealthService:
    """Build a HealthService through the canonical composition assembly path."""
    resolved_metrics = metrics or PrometheusMetrics()
    return HealthService(
        logger=logger,
        _factory=_HealthCheckDataSourceFactory(
            logger=logger,
            metrics=resolved_metrics,
            settings=settings,
        ),
        clock=SystemClock(),
    )
