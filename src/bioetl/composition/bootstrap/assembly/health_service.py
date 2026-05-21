"""Canonical assembly helpers for health services and listener dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bioetl.application.services.health_service import HealthService
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.composition.providers.registration import (
    resolve_provider_assembly_support,
)
from bioetl.domain.ports import MetricsPort, RunLedgerPort, RunManifestPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.time import SystemClock

__all__ = [
    "HealthServerDependencies",
    "create_health_server_dependencies",
    "create_health_service",
]


@dataclass(frozen=True, slots=True)
class HealthServerDependencies:
    """Dependencies required by the HTTP health server."""

    health_monitor: ProviderHealthMonitor
    metrics: MetricsPort
    run_manifest_port: RunManifestPort
    run_ledger_port: RunLedgerPort


@dataclass(frozen=True, slots=True)
class _HealthCheckDataSourceFactory:
    """Composition-aware factory wrapper for CLI/server health probes."""

    logger: object
    metrics: MetricsPort
    settings: object

    @staticmethod
    def list_providers() -> list[str]:
        return DataSourceFactory.list_providers()

    def create(self, provider: str) -> object:
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
    logger: object,
    settings: object,
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


def create_health_server_dependencies(
    *,
    metrics: MetricsPort | None = None,
    run_manifest_service_factory: Callable[[], object],
) -> HealthServerDependencies:
    """Build health-listener dependencies through one canonical assembly path."""
    resolved_metrics = metrics or PrometheusMetrics()
    health_monitor = ProviderHealthMonitor(metrics=resolved_metrics)
    run_manifest_service = run_manifest_service_factory()

    return HealthServerDependencies(
        health_monitor=health_monitor,
        metrics=resolved_metrics,
        run_manifest_port=run_manifest_service.manifest_port,
        run_ledger_port=run_manifest_service.ledger_port,
    )
