"""Health-server contracts for interface callers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.services.ops.bronze_cleanup_service import (
        BronzeCleanupResult,
    )
    from bioetl.domain.ports import (
        HealthMonitorPort,
        MetricsPort,
        RunManifestPort,
        WorkflowManifestPort,
    )


class HealthServerDependenciesProtocol(Protocol):
    """Typed view of health-server dependencies returned by bootstrap."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort
    run_manifest_port: RunManifestPort
    workflow_manifest_port: WorkflowManifestPort


class BronzeCleanupServiceProtocol(Protocol):
    """Typed view of the Bronze cleanup service used by the facade."""

    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> BronzeCleanupResult: ...
