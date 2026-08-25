"""Health-server contracts for interface callers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.ops.bronze_cleanup_service import (
        BronzeCleanupResult,
    )
    from bioetl.domain.ports import (
        CheckpointPort,
        HealthMonitorPort,
        MetricsPort,
        RunLedgerPort,
        RunManifestPort,
        WorkflowManifestPort,
    )


class HealthServerDependenciesProtocol(Protocol):
    """Typed view of health-server dependencies returned by bootstrap."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort
    run_manifest_port: RunManifestPort
    workflow_manifest_port: WorkflowManifestPort


class HealthListenerDependenciesProtocol(Protocol):
    """Typed view of health-listener dependencies exposed through health_api."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort
    checkpoint_port: CheckpointPort
    run_manifest_port: RunManifestPort
    run_ledger_port: RunLedgerPort
    workflow_manifest_port: WorkflowManifestPort
    metrics_exposition: object



class BronzeCleanupServiceProtocol(Protocol):
    """Typed view of the Bronze cleanup service used by the facade."""

    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> BronzeCleanupResult: ...
