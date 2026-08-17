"""Thin composition facade for service bootstrap entrypoints."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition._service_invocation import invoke_bootstrap as _invoke_bootstrap

if TYPE_CHECKING:
    from bioetl.composition._service_types import (
        AdrServicePort,
        AuditInspectionService,
        BronzeCleanupResult,
        BronzeCleanupService,
        CheckpointService,
        ConfigService,
        ContractMigrationService,
        ExportService,
        ForensicRunDiffService,
        HealthService,
        HistoricalReplayClosureService,
        HistoricalReplayCorpusService,
        HistoricalReplayUniverseService,
        LineageInspectionService,
        LockPort,
        LockService,
        MetricsService,
        ObservabilityWorkflowService,
        PipelineRegistry,
        PipelineRunnerService,
        QuarantinePort,
        QuarantineService,
        RunManifestInspectionService,
        VacuumService,
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
_BOOTSTRAP_STORAGE_EXPORT_MODULE = "bioetl.composition.bootstrap.cli.storage"
_BOOTSTRAP_CLI_MODULE = "bioetl.composition.bootstrap.cli"


_BOOTSTRAP_EXPORTS: dict[str, str] = {
    "bootstrap_adr_service": _BOOTSTRAP_CLI_MODULE,
    "bootstrap_audit_inspection_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_bronze_cleanup_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_checkpoint_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_config_service": "bioetl.composition.bootstrap.cli.config",
    "bootstrap_contract_migration_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_export_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
    "bootstrap_forensic_run_diff_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_corpus_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_closure_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_historical_replay_universe_service": _RUN_MANIFEST_BOOTSTRAP,
    "bootstrap_health_server_dependencies": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_health_service": "bioetl.composition.bootstrap.cli.health",
    "bootstrap_lineage_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_lock_service": "bioetl.composition.bootstrap.cli.lock",
    "bootstrap_metrics_service": "bioetl.composition.bootstrap.cli.metrics",
    "bootstrap_observability_workflow_service": (
        "bioetl.composition.bootstrap.cli.checkpoint"
    ),
    "bootstrap_pipeline_runner_service": "bioetl.composition.bootstrap.runtime.runner",
    "bootstrap_quarantine_adapter": (
        "bioetl.composition.bootstrap.assembly.checkpoint"
    ),
    "bootstrap_quarantine_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_run_manifest_service": _BOOTSTRAP_CHECKPOINT_EXPORT_MODULE,
    "bootstrap_vacuum_service": _BOOTSTRAP_STORAGE_EXPORT_MODULE,
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
    from bioetl.composition._registration import ensure_runtime_registrations

    ensure_runtime_registrations(registry=registry, scope=scope)


def _ensure_provider_registrations() -> None:
    """Ensure provider adapters only, without full pipeline factory registration."""
    _ensure_registrations(scope="providers")


def _ensure_pipeline_registrations(registry: PipelineRegistry | None = None) -> None:
    """Ensure full provider and pipeline factory registration."""
    _ensure_registrations(registry=registry, scope="pipelines")


def get_checkpoint_service() -> CheckpointService:
    """Get checkpoint administration service."""
    _ensure_provider_registrations()
    return cast("CheckpointService", _invoke_bootstrap("bootstrap_checkpoint_service"))


def get_audit_service() -> AuditInspectionService:
    """Get an audit inspection service for operator diagnostics operations."""
    _ensure_provider_registrations()
    return cast(
        "AuditInspectionService",
        _invoke_bootstrap("bootstrap_audit_inspection_service"),
    )


def get_quarantine_service(*, data_root: Path | None = None) -> QuarantineService:
    """Get quarantine administration service without pipeline registration."""
    if data_root is None:
        return cast(
            "QuarantineService", _invoke_bootstrap("bootstrap_quarantine_service")
        )
    return cast(
        "QuarantineService",
        _invoke_bootstrap("bootstrap_quarantine_service", data_root=data_root),
    )


def get_bronze_cleanup_service() -> BronzeCleanupService:
    """Get Bronze cleanup service."""
    _ensure_provider_registrations()
    return cast(
        "BronzeCleanupService", _invoke_bootstrap("bootstrap_bronze_cleanup_service")
    )


def get_vacuum_service() -> VacuumService:
    """Get batch vacuum service."""
    _ensure_provider_registrations()
    return cast("VacuumService", _invoke_bootstrap("bootstrap_vacuum_service"))


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
    _ensure_pipeline_registrations(registry=registry)
    return cast(
        "PipelineRunnerService",
        _invoke_bootstrap("bootstrap_pipeline_runner_service", registry=registry),
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


def get_contract_migration_service() -> ContractMigrationService:
    """Get the contract migration planner service."""
    _ensure_provider_registrations()
    return cast(
        "ContractMigrationService",
        _invoke_bootstrap("bootstrap_contract_migration_service"),
    )


def get_health_service() -> HealthService:
    """Get provider health service."""
    _ensure_provider_registrations()
    return cast("HealthService", _invoke_bootstrap("bootstrap_health_service"))


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Get workflow-level observability diagnostics helpers."""
    _ensure_provider_registrations()
    return cast(
        "ObservabilityWorkflowService",
        _invoke_bootstrap("bootstrap_observability_workflow_service"),
    )


def get_health_server_dependencies(
    *,
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Get health-server dependencies without pipeline registration."""
    if data_root is None:
        return cast(
            "HealthServerDependencies",
            _invoke_bootstrap("bootstrap_health_server_dependencies"),
        )
    return cast(
        "HealthServerDependencies",
        _invoke_bootstrap(
            "bootstrap_health_server_dependencies",
            data_root=data_root,
        ),
    )


def get_metrics_service() -> MetricsService:
    """Get metrics administration service."""
    _ensure_provider_registrations()
    return cast("MetricsService", _invoke_bootstrap("bootstrap_metrics_service"))


def get_quarantine_port() -> QuarantinePort:
    """Get the shared low-level quarantine port without pipeline registration."""
    return cast("QuarantinePort", _invoke_bootstrap("bootstrap_quarantine_adapter"))


def get_adr_service() -> AdrServicePort:
    """Get ADR management port."""
    _ensure_provider_registrations()
    return cast("AdrServicePort", _invoke_bootstrap("bootstrap_adr_service"))


def get_config_service() -> ConfigService:
    """Get application configuration service."""
    _ensure_provider_registrations()
    return cast("ConfigService", _invoke_bootstrap("bootstrap_config_service"))


def get_export_service() -> ExportService:
    """Get Delta export service."""
    _ensure_provider_registrations()
    return cast("ExportService", _invoke_bootstrap("bootstrap_export_service"))


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Get forensic run diff service."""
    _ensure_provider_registrations()
    return cast(
        "ForensicRunDiffService",
        _invoke_bootstrap("bootstrap_forensic_run_diff_service"),
    )


def get_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Get historical replay closure service."""
    _ensure_provider_registrations()
    return cast(
        "HistoricalReplayClosureService",
        _invoke_bootstrap("bootstrap_historical_replay_closure_service"),
    )


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Get historical replay corpus service."""
    _ensure_provider_registrations()
    return cast(
        "HistoricalReplayCorpusService",
        _invoke_bootstrap("bootstrap_historical_replay_corpus_service"),
    )


def get_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Get historical replay universe service."""
    _ensure_provider_registrations()
    return cast(
        "HistoricalReplayUniverseService",
        _invoke_bootstrap("bootstrap_historical_replay_universe_service"),
    )


def get_lineage_service() -> LineageInspectionService:
    """Get lineage service."""
    _ensure_provider_registrations()
    return cast(
        "LineageInspectionService", _invoke_bootstrap("bootstrap_lineage_service")
    )


def get_lock_service() -> LockService:
    """Get administrative lock service."""
    _ensure_provider_registrations()
    return cast("LockService", _invoke_bootstrap("bootstrap_lock_service"))


def get_run_manifest_service() -> RunManifestInspectionService:
    """Get run-manifest service without full pipeline registration."""
    _ensure_provider_registrations()
    return cast(
        "RunManifestInspectionService",
        _invoke_bootstrap("bootstrap_run_manifest_service"),
    )
