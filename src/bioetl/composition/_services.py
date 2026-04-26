"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition._service_bootstraps import (
    bootstrap_adr_service,
    bootstrap_bronze_cleanup_service,
    bootstrap_checkpoint_service,
    bootstrap_config_service,
    bootstrap_export_service,
    bootstrap_health_server_dependencies,
    bootstrap_health_service,
    bootstrap_lock_service,
    bootstrap_metrics_service,
    bootstrap_pipeline_runner_service,
    bootstrap_quarantine_port,
    bootstrap_quarantine_service,
    bootstrap_vacuum_service,
    resolve_bootstrap_attr,
)

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.application.services.vacuum_service import VacuumService
    from bioetl.composition import PipelineRegistry
    from bioetl.composition.health_api import HealthServerDependenciesProtocol
    from bioetl.domain.ports import QuarantinePort
    from bioetl.domain.workflow import WorkflowConfig


class _BronzeCleanupServiceProtocol(Protocol):
    async def cleanup(
        self,
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> BronzeCleanupResult: ...


__all__ = [
    "cleanup_bronze",
    "get_adr_service",
    "get_audit_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_service",
    "get_config_service",
    "get_contract_migration_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lineage_service",
    "get_lock_service",
    "get_metrics_service",
    "get_observability_workflow_service",
    "get_pipeline_runner_service",
    "get_quarantine_port",
    "get_quarantine_service",
    "get_run_manifest_service",
    "get_vacuum_service",
    "load_workflow_config",
]


def _resolve_bootstrap_callable(name: str) -> Callable[[], object]:
    """Resolve dynamically exported bootstrap hooks as zero-arg callables."""
    return cast("Callable[[], object]", resolve_bootstrap_attr(name))


def _ensure_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure providers and pipelines are registered lazily to avoid cycles."""
    from bioetl.composition._pipeline_execution import (
        _ensure_registrations as ensure_registrations_impl,
    )

    ensure_registrations_impl(registry=registry)


def get_checkpoint_service() -> CheckpointService:
    """Get checkpoint administration service."""
    _ensure_registrations()
    return cast("CheckpointService", bootstrap_checkpoint_service())


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_audit_inspection_service")
    return bootstrap()


def get_quarantine_service() -> QuarantineService:
    """Get quarantine administration service."""
    _ensure_registrations()
    return cast("QuarantineService", bootstrap_quarantine_service())


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get Bronze cleanup service."""
    _ensure_registrations()
    return cast("BronzeCleanupService", bootstrap_bronze_cleanup_service())


def get_vacuum_service() -> VacuumService:
    """Get batch vacuum service."""
    _ensure_registrations()
    return cast("VacuumService", bootstrap_vacuum_service())


def get_export_service() -> ExportService:
    """Get Delta export service."""
    _ensure_registrations()
    return cast("ExportService", bootstrap_export_service())


def get_lock_service() -> LockService:
    """Get administrative lock service."""
    _ensure_registrations()
    return cast("LockService", bootstrap_lock_service())


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up Bronze files based on retention policy."""
    service = cast(_BronzeCleanupServiceProtocol, get_bronze_cleanup_service())
    result = await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )
    return result


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Get universal pipeline runner service."""
    _ensure_registrations(registry=registry)
    return cast(
        "PipelineRunnerService",
        bootstrap_pipeline_runner_service(registry=registry),
    )


def get_config_service() -> object:
    """Get application configuration service."""
    _ensure_registrations()
    return bootstrap_config_service()


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical composition service seam."""
    from bioetl.infrastructure.config.workflow_config_api import (
        load_workflow_config as load_workflow_config_impl,
    )

    return load_workflow_config_impl(name)


def get_contract_migration_service() -> object:
    """Get the contract migration planner service."""
    _ensure_registrations()
    bootstrap = cast(
        "Callable[[], object]",
        resolve_bootstrap_attr("bootstrap_contract_migration_service"),
    )
    return bootstrap()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get a run-manifest inspection service for control-plane operations."""
    _ensure_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_run_manifest_service")
    return bootstrap()


def get_lineage_service() -> LineageInspectionService:
    """Get a lineage inspection service for traceability operations."""
    _ensure_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_lineage_service")
    return bootstrap()


def get_health_service() -> HealthService:
    """Get provider health service."""
    _ensure_registrations()
    return cast("HealthService", bootstrap_health_service())


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_registrations()
    bootstrap = _resolve_bootstrap_callable("bootstrap_observability_workflow_service")
    return bootstrap()


def get_health_server_dependencies() -> HealthServerDependenciesProtocol:
    """Get dependencies for the health server."""
    _ensure_registrations()
    return cast(
        "HealthServerDependenciesProtocol",
        bootstrap_health_server_dependencies(),
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_registrations()
    return cast("MetricsService", bootstrap_metrics_service())


def get_adr_service() -> object:
    """Get ADR management port."""
    _ensure_registrations()
    return bootstrap_adr_service()


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port."""
    _ensure_registrations()
    return cast("QuarantinePort", bootstrap_quarantine_port())
