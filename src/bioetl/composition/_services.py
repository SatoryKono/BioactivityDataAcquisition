"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap.service_registry_contracts import (
    AdrServicePort,
    AuditInspectionServiceProtocol,
    BronzeCleanupServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    ForensicRunDiffServiceProtocol,
    HealthServerDependenciesFactoryProtocol,
    HealthServiceProtocol,
    HistoricalReplayClosureServiceProtocol,
    HistoricalReplayCorpusServiceProtocol,
    HistoricalReplayUniverseServiceProtocol,
    LineageInspectionServiceProtocol,
    LockServiceProtocol,
    MetricsService,
    ObservabilityWorkflowServiceProtocol,
    PipelineRunnerServiceFactoryProtocol,
    QuarantinePort,
    QuarantineServiceFactoryProtocol,
    RunManifestInspectionServiceProtocol,
    VacuumServiceProtocol,
    WorkflowInspectionServiceProtocol,
)
from bioetl.composition._registration import ensure_runtime_registrations
from bioetl.composition._service_registry import resolve as _resolve
from bioetl.composition._service_registry import typed_port as _typed_port
from bioetl.composition.contracts.factories import (
    HealthServerDependenciesFactoryProtocol,
    PipelineRunnerServiceFactoryProtocol,
    QuarantineServiceFactoryProtocol,
)
from bioetl.composition.contracts.health import BronzeCleanupServiceProtocol
from bioetl.composition.registry_api import create_registry
from bioetl.domain.ports import AdrServicePort, QuarantinePort

if TYPE_CHECKING:
    from bioetl.composition._service_types import (
        BronzeCleanupResult,
        LockPort,
        PipelineRegistry,
        PipelineRunnerService,
        QuarantineService,
        WorkflowConfig,
        WorkflowExecutionService,
        WorkflowRunnerService,
    )
    from bioetl.composition.bootstrap.assembly.health_server import (
        HealthServerDependencies,
    )


def _ensure_registrations(
    registry: PipelineRegistry | None = None,
    *,
    scope: str = "pipelines",
) -> None:
    """Ensure the requested runtime registration scope lazily."""
    ensure_runtime_registrations(registry=registry, scope=scope)


def _ensure_provider_registrations() -> None:
    """Ensure provider adapters only, without full pipeline factory registration."""
    _ensure_registrations(scope="providers")


def _ensure_pipeline_registrations(
    registry: PipelineRegistry | None = None,
) -> PipelineRegistry:
    """Return an explicit registry with provider and pipeline registrations."""
    if registry is None:
        registry = create_registry()
    _ensure_registrations(registry=registry, scope="pipelines")
    return registry


def get_checkpoint_service() -> CheckpointServiceProtocol:
    """Get checkpoint administration service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[CheckpointServiceProtocol](CheckpointServiceProtocol))


def get_audit_service() -> AuditInspectionServiceProtocol:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[AuditInspectionServiceProtocol](AuditInspectionServiceProtocol)
    )


def get_quarantine_service(*, data_root: Path | None = None) -> QuarantineService:
    """Get quarantine administration service without pipeline registration."""
    factory = _resolve(
        _typed_port[QuarantineServiceFactoryProtocol](QuarantineServiceFactoryProtocol)
    )
    return factory(data_root=data_root)


def get_bronze_cleanup_service() -> BronzeCleanupServiceProtocol:
    """Get Bronze cleanup service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[BronzeCleanupServiceProtocol](BronzeCleanupServiceProtocol)
    )


def get_vacuum_service() -> VacuumServiceProtocol:
    """Get batch vacuum service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[VacuumServiceProtocol](VacuumServiceProtocol))


async def cleanup_bronze(
    retention_days: int = 90,
    dry_run: bool = False,
) -> BronzeCleanupResult:
    """Clean up Bronze files based on retention policy."""
    service = get_bronze_cleanup_service()
    return await service.cleanup(
        retention_days=retention_days,
        dry_run=dry_run,
    )


def get_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Get universal pipeline runner service."""
    effective_registry = _ensure_pipeline_registrations(registry=registry)
    factory = _resolve(
        _typed_port[PipelineRunnerServiceFactoryProtocol](
            PipelineRunnerServiceFactoryProtocol
        )
    )
    return factory(registry=effective_registry)


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowRunnerService:
    """Build workflow runner service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_runner_service(registry=registry)


def _workflow_services_module() -> ModuleType:
    """Resolve the workflow composition module through one lazy boundary."""
    from bioetl.composition import _workflow_services

    return _workflow_services


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
    workflow_lock_port: LockPort | None = None,
) -> WorkflowExecutionService:
    """Build workflow execution service via the canonical workflow seam."""
    return _workflow_services_module().get_workflow_execution_service(
        registry=registry,
        workflow_lock_port=workflow_lock_port,
    )


def get_workflow_inspection_service() -> WorkflowInspectionServiceProtocol:
    """Build workflow inspection service via the canonical workflow seam."""
    return _resolve(
        _typed_port[WorkflowInspectionServiceProtocol](WorkflowInspectionServiceProtocol)
    )


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical workflow seam."""
    return _workflow_services_module().load_workflow_config(name)


def get_contract_migration_service() -> ContractMigrationServiceProtocol:
    """Get the contract migration planner service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[ContractMigrationServiceProtocol](ContractMigrationServiceProtocol)
    )


def get_health_service() -> HealthServiceProtocol:
    """Get provider health service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[HealthServiceProtocol](HealthServiceProtocol))


def get_observability_workflow_service() -> ObservabilityWorkflowServiceProtocol:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[ObservabilityWorkflowServiceProtocol](
            ObservabilityWorkflowServiceProtocol
        )
    )


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Get health-server dependencies without pipeline registration."""
    factory = _resolve(
        _typed_port[HealthServerDependenciesFactoryProtocol](
            HealthServerDependenciesFactoryProtocol
        )
    )
    return cast(
        "HealthServerDependencies",
        cast(object, factory(data_root=data_root)),
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[MetricsService](MetricsService))


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port without pipeline registration."""
    return _resolve(_typed_port[QuarantinePort](QuarantinePort))


def get_adr_service() -> AdrServicePort:
    """Get ADR management port."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[AdrServicePort](AdrServicePort))


def get_config_service() -> ConfigServiceProtocol:
    """Get application configuration service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[ConfigServiceProtocol](ConfigServiceProtocol))


def get_export_service() -> ExportServiceProtocol:
    """Get Delta export service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[ExportServiceProtocol](ExportServiceProtocol))


def get_forensic_run_diff_service() -> ForensicRunDiffServiceProtocol:
    """Get forensic run diff service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[ForensicRunDiffServiceProtocol](ForensicRunDiffServiceProtocol)
    )


def get_historical_replay_closure_service() -> HistoricalReplayClosureServiceProtocol:
    """Get historical replay closure service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[HistoricalReplayClosureServiceProtocol](
            HistoricalReplayClosureServiceProtocol
        )
    )


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusServiceProtocol:
    """Get historical replay corpus service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[HistoricalReplayCorpusServiceProtocol](
            HistoricalReplayCorpusServiceProtocol
        )
    )


def get_historical_replay_universe_service() -> HistoricalReplayUniverseServiceProtocol:
    """Get historical replay universe service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[HistoricalReplayUniverseServiceProtocol](
            HistoricalReplayUniverseServiceProtocol
        )
    )


def get_lineage_service() -> LineageInspectionServiceProtocol:
    """Get lineage service."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[LineageInspectionServiceProtocol](LineageInspectionServiceProtocol)
    )


def get_lock_service() -> LockServiceProtocol:
    """Get administrative lock service."""
    _ensure_provider_registrations()
    return _resolve(_typed_port[LockServiceProtocol](LockServiceProtocol))


def get_run_manifest_service() -> RunManifestInspectionServiceProtocol:
    """Get run-manifest service without full pipeline registration."""
    _ensure_provider_registrations()
    return _resolve(
        _typed_port[RunManifestInspectionServiceProtocol](
            RunManifestInspectionServiceProtocol
        )
    )
