"""Application services for cross-cutting concerns.

Implements RULES.md §4 - Application Layer services.
These services coordinate business logic and are injected into runners.

Administrative services for CLI operations:
- CheckpointService: Checkpoint listing, deletion, inspection
- QuarantineService: Quarantine inspection, replay, purge
- LockService: Lock management (import from lock_service submodule)
- BronzeCleanupService: Bronze retention cleanup
- PipelineRunnerService: Universal pipeline execution
- ConfigService: Configuration access and validation
- HealthService: Provider health checking

Internal DTOs and result types not re-exported here should be imported
directly from their defining submodules:
- ``bioetl.application.services.dq_report_service``
- ``bioetl.application.services.lock_service``
- ``bioetl.application.services.shutdown_service``
- ``bioetl.application.services.metrics_service``
- ``bioetl.application.services.medallion_lifecycle``
"""

from __future__ import annotations

from importlib import import_module

_LAZY_EXPORT_MODULES: dict[str, str] = {
    "AuditInspectionResult": "bioetl.application.services.audit_inspection_service",
    "AuditInspectionService": "bioetl.application.services.audit_inspection_service",
    "AuditRunWorkflowResult": (
        "bioetl.application.services.observability_workflow_service"
    ),
    "BronzeCleanupResult": "bioetl.application.services.bronze_cleanup_service",
    "BronzeCleanupService": "bioetl.application.services.bronze_cleanup_service",
    "CheckpointAuditWorkflowResult": (
        "bioetl.application.services.observability_workflow_service"
    ),
    "CheckpointService": "bioetl.application.services.checkpoint_service",
    "ColumnInfo": "bioetl.application.services.export_service",
    "ConfigService": "bioetl.application.services.config_service",
    "ContractMigrationAction": (
        "bioetl.application.services.contract_migration_service"
    ),
    "ContractMigrationPlan": "bioetl.application.services.contract_migration_service",
    "ContractMigrationService": (
        "bioetl.application.services.contract_migration_service"
    ),
    "ContractVersionTransition": (
        "bioetl.application.services.contract_migration_service"
    ),
    "ExportOptions": "bioetl.application.services.export_service",
    "ExportResult": "bioetl.application.services.export_service",
    "ExportService": "bioetl.application.services.export_service",
    "HealthService": "bioetl.application.services.health_service",
    "LineageFragmentInspectionResult": (
        "bioetl.application.services.lineage_inspection_service"
    ),
    "LineageInspectionService": (
        "bioetl.application.services.lineage_inspection_service"
    ),
    "LineageNodeRelation": "bioetl.application.services.lineage_inspection_service",
    "LineageRunExplanationResult": (
        "bioetl.application.services.lineage_inspection_service"
    ),
    "LineageTraceResult": "bioetl.application.services.lineage_inspection_service",
    "MetricsService": "bioetl.application.services.metrics_service",
    "ObservabilityWorkflowService": (
        "bioetl.application.services.observability_workflow_service"
    ),
    "PipelineNotFoundError": "bioetl.application.services.pipeline_runner_service",
    "PipelineRunLifecycleService": (
        "bioetl.application.services.pipeline_run_lifecycle_service"
    ),
    "PipelineRunResult": "bioetl.application.services.pipeline_runner_service",
    "PipelineRunnerService": "bioetl.application.services.pipeline_runner_service",
    "QuarantineService": "bioetl.application.services.quarantine_service",
    "RunManifestDiffEntry": (
        "bioetl.application.services.run_manifest_inspection_service"
    ),
    "RunManifestDiffResult": (
        "bioetl.application.services.run_manifest_inspection_service"
    ),
    "RunManifestInspectionResult": (
        "bioetl.application.services.run_manifest_inspection_service"
    ),
    "RunManifestInspectionService": (
        "bioetl.application.services.run_manifest_inspection_service"
    ),
    "RunOptions": "bioetl.application.services.pipeline_runner_service",
    "RunResult": "bioetl.application.services.pipeline_runner_service",
    "TableInfo": "bioetl.application.services.export_service",
    "TablePreview": "bioetl.application.services.export_service",
    "TableVacuumResult": "bioetl.application.services.vacuum_service",
    "VacuumAllResult": "bioetl.application.services.vacuum_service",
    "VacuumService": "bioetl.application.services.vacuum_service",
}

__all__ = [
    "AuditInspectionResult",
    "AuditInspectionService",
    "AuditRunWorkflowResult",
    "BronzeCleanupResult",
    "BronzeCleanupService",
    "CheckpointAuditWorkflowResult",
    "CheckpointService",
    "ColumnInfo",
    "ConfigService",
    "ContractMigrationAction",
    "ContractMigrationPlan",
    "ContractMigrationService",
    "ContractVersionTransition",
    "ExportOptions",
    "ExportResult",
    "ExportService",
    "HealthService",
    "LineageFragmentInspectionResult",
    "LineageInspectionService",
    "LineageNodeRelation",
    "LineageRunExplanationResult",
    "LineageTraceResult",
    "MetricsService",
    "ObservabilityWorkflowService",
    "PipelineNotFoundError",
    "PipelineRunLifecycleService",
    "PipelineRunResult",
    "PipelineRunnerService",
    "QuarantineService",
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
    "RunOptions",
    "RunResult",
    "TableInfo",
    "TablePreview",
    "TableVacuumResult",
    "VacuumAllResult",
    "VacuumService",
]


def __getattr__(name: str) -> object:
    """Resolve service facade exports lazily to avoid broad import fan-out."""
    try:
        module_name = _LAZY_EXPORT_MODULES[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable service exports for introspection."""
    return sorted(set(globals()) | set(__all__))
