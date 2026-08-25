"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.ports.metrics import MetricsService
from bioetl.application.ports.operations import (
    AuditInspectionServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    LockServiceProtocol,
    ObservabilityWorkflowServiceProtocol,
    VacuumServiceProtocol,
)
from bioetl.composition._registration import ensure_runtime_registrations
from bioetl.composition._service_invocation import invoke_bootstrap as _invoke_bootstrap
from bioetl.composition._service_registry import resolve as _resolve
from bioetl.composition.contracts.health import BronzeCleanupServiceProtocol
from bioetl.composition.registry_api import create_registry
from bioetl.domain.ports.adr import AdrServicePort
from bioetl.domain.ports.quality.quarantine import QuarantinePort

if TYPE_CHECKING:
    from bioetl.application.ports.health import HealthServiceProtocol
    from bioetl.composition._service_types import (
        BronzeCleanupResult,
        ForensicRunDiffService,
        HistoricalReplayClosureService,
        HistoricalReplayCorpusService,
        HistoricalReplayUniverseService,
        LineageInspectionService,
        LockPort,
        PipelineRegistry,
        PipelineRunnerService,
        QuarantineService,
        RunManifestInspectionService,
        WorkflowConfig,
        WorkflowExecutionService,
        WorkflowInspectionService,
        WorkflowRunnerService,
    )
    from bioetl.composition.bootstrap.assembly.health_server import (
        HealthServerDependencies,
    )


_BOOTSTRAP_CHECKPOINT_EXPORT_MODULE = "bioetl.composition.bootstrap.cli.checkpoint"
_RUN_MANIFEST_BOOTSTRAP = "bioetl.composition.bootstrap.cli.run_manifest"


_BOOTSTRAP_EXPORTS: dict[str, str] = {
    "bootstrap_forensic_run_diff_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_corpus_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_closure_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_universe_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_health_server_dependencies": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_lineage_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_pipeline_runner_service": "bioetl.composition.bootstrap.runtime.runner",
    "bootstrap_quarantine_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_run_manifest_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
}


def resolve_bootstrap_attr(name: str) -> object:
    """Resolve one public bootstrap export lazily without invoking it."""
    export = _BOOTSTRAP_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"Unknown bootstrap export: {name!r}")
    bootstrap_attr: object = getattr(import_module(export), name)
    return bootstrap_attr


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
    return _resolve(CheckpointServiceProtocol)


def get_audit_service() -> AuditInspectionServiceProtocol:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_provider_registrations()
    return _resolve(AuditInspectionServiceProtocol)


def get_quarantine_service(*, data_root: Path | None = None) -> QuarantineService:
    """Get quarantine administration service without pipeline registration."""
    if data_root is None:
        return _invoke_bootstrap("bootstrap_quarantine_service")
    return _invoke_bootstrap("bootstrap_quarantine_service", data_root=data_root)


def get_bronze_cleanup_service() -> BronzeCleanupServiceProtocol:
    """Get Bronze cleanup service."""
    _ensure_provider_registrations()
    return _resolve(BronzeCleanupServiceProtocol)


def get_vacuum_service() -> VacuumServiceProtocol:
    """Get batch vacuum service."""
    _ensure_provider_registrations()
    return _resolve(VacuumServiceProtocol)


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
    return _invoke_bootstrap(
        "bootstrap_pipeline_runner_service",
        registry=effective_registry,
    )


def get_workflow_runner_service(
    registry: PipelineRegistry | None = None,
) -> WorkflowRunnerService:
    """Build workflow runner service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_runner_service(registry=registry)


def get_workflow_execution_service(
    registry: PipelineRegistry | None = None,
    workflow_lock_port: LockPort | None = None,
) -> WorkflowExecutionService:
    """Build workflow execution service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_execution_service(
        registry=registry,
        workflow_lock_port=workflow_lock_port,
    )


def get_workflow_inspection_service() -> WorkflowInspectionService:
    """Build workflow inspection service via the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.get_workflow_inspection_service()


def load_workflow_config(name: str) -> WorkflowConfig:
    """Load workflow YAML through the canonical workflow seam."""
    from bioetl.composition import _workflow_services

    return _workflow_services.load_workflow_config(name)


def get_contract_migration_service() -> ContractMigrationServiceProtocol:
    """Get the contract migration planner service."""
    _ensure_provider_registrations()
    return _resolve(ContractMigrationServiceProtocol)


def get_health_service() -> HealthServiceProtocol:
    """Get provider health service."""
    _ensure_provider_registrations()
    health_ports = import_module("bioetl.application.ports.health")
    return _resolve(health_ports.HealthServiceProtocol)


def get_observability_workflow_service() -> ObservabilityWorkflowServiceProtocol:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_provider_registrations()
    return _resolve(ObservabilityWorkflowServiceProtocol)


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Get health-server dependencies without pipeline registration."""
    if data_root is None:
        return _invoke_bootstrap("bootstrap_health_server_dependencies")
    return _invoke_bootstrap(
        "bootstrap_health_server_dependencies",
        data_root=data_root,
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_provider_registrations()
    return _resolve(MetricsService)


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port without pipeline registration."""
    return _resolve(QuarantinePort)


def get_adr_service() -> AdrServicePort:
    """Get ADR management port."""
    _ensure_provider_registrations()
    return _resolve(AdrServicePort)


def get_config_service() -> ConfigServiceProtocol:
    """Get application configuration service."""
    _ensure_provider_registrations()
    return _resolve(ConfigServiceProtocol)


def get_export_service() -> ExportServiceProtocol:
    """Get Delta export service."""
    _ensure_provider_registrations()
    return _resolve(ExportServiceProtocol)


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Get forensic run diff service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_forensic_run_diff_service")


def get_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Get historical replay closure service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_closure_service")


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Get historical replay corpus service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_corpus_service")


def get_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Get historical replay universe service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_historical_replay_universe_service")


def get_lineage_service() -> LineageInspectionService:
    """Get lineage service."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_lineage_service")


def get_lock_service() -> LockServiceProtocol:
    """Get administrative lock service."""
    _ensure_provider_registrations()
    return _resolve(LockServiceProtocol)


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get run-manifest service without full pipeline registration."""
    _ensure_provider_registrations()
    return _invoke_bootstrap("bootstrap_run_manifest_service")
