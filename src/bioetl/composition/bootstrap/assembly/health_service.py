"""Canonical assembly helpers for health services and listener dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.services.ops.health_service import HealthService
from bioetl.composition.bootstrap.assembly.health_server import (
    HealthServerDependencies,
    create_health_server_dependencies,
)
from bioetl.composition.composite_catalog import load_pipeline_config
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.composition.providers.provider_registry import (
    resolve_provider_registry,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderDataSourceAccessProtocol,
)
from bioetl.composition.providers.registration import (
    resolve_provider_assembly_support,
)
from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "HealthServerDependencies",
    "create_health_server_dependencies",
    "create_health_service",
]

# Providers whose registry adapter_class is a composite DataSourcePort that must
# be built through data_source_creator (not raw adapter_class(**kwargs)).
_DATA_SOURCE_CREATOR_HEALTH_PROVIDERS = frozenset({"uniprot_idmapping"})


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
        if provider in _DATA_SOURCE_CREATOR_HEALTH_PROVIDERS:
            return self._create_via_data_source_creator(provider)

        support = resolve_provider_assembly_support(None)
        http_client = support.create_http_client(
            provider,
            self.settings,
            metrics=self.metrics,
        )
        return DataSourceFactory.create(
            provider,
            http_client=cast("UnifiedHTTPClient | None", http_client),
            logger=self.logger,
            settings=self.settings,
            metrics=self.metrics,
        )

    def _create_via_data_source_creator(self, provider: str) -> DataSourcePort:
        """Build composite providers (e.g. ID mapping) for health probes."""
        registry = cast(
            ProviderDataSourceAccessProtocol,
            resolve_provider_registry(None, ensure_ready=True),
        )
        pipeline_config = load_pipeline_config(provider)
        return registry.create_data_source(
            provider,
            settings=self.settings,
            pipeline_config=pipeline_config,
            logger=self.logger,
            metrics=self.metrics,
            pipeline_name=f"health_{provider}",
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
