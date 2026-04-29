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

Canonical semantic seams:
- ``bioetl.application.services.control_plane``
- ``bioetl.application.services.lineage``
- ``bioetl.application.services.execution``

Legacy flat module paths remain as compatibility facades and should not be used
for new imports.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

_OBSERVABILITY_WORKFLOW_SERVICE_MODULE = (
    "bioetl.application.services.observability_workflow_service"
)
_EXPORT_SERVICE_MODULE = "bioetl.application.services.export_service"
_LINEAGE_INSPECTION_SERVICE_MODULE = (
    "bioetl.application.services.lineage.lineage_inspection_service"
)
_PIPELINE_RUNNER_SERVICE_MODULE = (
    "bioetl.application.services.execution.pipeline_runner_service"
)
_CONTRACT_MIGRATION_SERVICE_MODULE = (
    "bioetl.application.services.contract_migration_service"
)
_RUN_MANIFEST_INSPECTION_SERVICE_MODULE = (
    "bioetl.application.services.control_plane.run_manifest_inspection_service"
)
_VACUUM_SERVICE_MODULE = "bioetl.application.services.vacuum_service"

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionResult,
        AuditInspectionService,
    )
    from bioetl.application.services.bronze_cleanup_service import (
        BronzeCleanupResult,
        BronzeCleanupService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.config_service import ConfigService
    from bioetl.application.services.contract_migration_service import (
        ContractMigrationAction,
        ContractMigrationPlan,
        ContractMigrationService,
        ContractVersionTransition,
    )
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestDiffEntry,
        RunManifestDiffResult,
        RunManifestInspectionResult,
        RunManifestInspectionService,
    )
    from bioetl.application.services.execution.pipeline_run_lifecycle_service import (
        PipelineRunLifecycleService,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineNotFoundError,
        PipelineRunResult,
        RunOptions,
        RunResult,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.application.services.export_models import (
        ColumnInfo,
        ExportOptions,
        ExportResult,
        TableInfo,
        TablePreview,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageFragmentInspectionResult,
        LineageInspectionService,
        LineageNodeRelationResult,
        LineageRunExplanationResult,
        LineageTraceResult,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        AuditRunWorkflowResult,
        CheckpointAuditWorkflowResult,
        ObservabilityWorkflowService,
        RunForensicDossierResult,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.application.services.vacuum_service import (
        TableVacuumResult,
        VacuumAllResult,
        VacuumService,
    )

_LAZY_EXPORT_MODULES: dict[str, str] = {
    "AuditInspectionResult": "bioetl.application.services.audit_inspection_service",
    "AuditInspectionService": "bioetl.application.services.audit_inspection_service",
    "AuditRunWorkflowResult": _OBSERVABILITY_WORKFLOW_SERVICE_MODULE,
    "BronzeCleanupResult": "bioetl.application.services.bronze_cleanup_service",
    "BronzeCleanupService": "bioetl.application.services.bronze_cleanup_service",
    "CheckpointAuditWorkflowResult": _OBSERVABILITY_WORKFLOW_SERVICE_MODULE,
    "RunForensicDossierResult": _OBSERVABILITY_WORKFLOW_SERVICE_MODULE,
    "CheckpointService": "bioetl.application.services.checkpoint_service",
    "ColumnInfo": _EXPORT_SERVICE_MODULE,
    "ConfigService": "bioetl.application.services.config_service",
    "ContractMigrationAction": _CONTRACT_MIGRATION_SERVICE_MODULE,
    "ContractMigrationPlan": _CONTRACT_MIGRATION_SERVICE_MODULE,
    "ContractMigrationService": _CONTRACT_MIGRATION_SERVICE_MODULE,
    "ContractVersionTransition": _CONTRACT_MIGRATION_SERVICE_MODULE,
    "ExportOptions": _EXPORT_SERVICE_MODULE,
    "ExportResult": _EXPORT_SERVICE_MODULE,
    "ExportService": _EXPORT_SERVICE_MODULE,
    "HealthService": "bioetl.application.services.health_service",
    "LineageFragmentInspectionResult": _LINEAGE_INSPECTION_SERVICE_MODULE,
    "LineageInspectionService": _LINEAGE_INSPECTION_SERVICE_MODULE,
    "LineageNodeRelationResult": _LINEAGE_INSPECTION_SERVICE_MODULE,
    "LineageRunExplanationResult": _LINEAGE_INSPECTION_SERVICE_MODULE,
    "LineageTraceResult": _LINEAGE_INSPECTION_SERVICE_MODULE,
    "MetricsService": "bioetl.application.services.metrics_service",
    "ObservabilityWorkflowService": _OBSERVABILITY_WORKFLOW_SERVICE_MODULE,
    "PipelineNotFoundError": _PIPELINE_RUNNER_SERVICE_MODULE,
    "PipelineRunLifecycleService": (
        "bioetl.application.services.execution.pipeline_run_lifecycle_service"
    ),
    "PipelineRunResult": _PIPELINE_RUNNER_SERVICE_MODULE,
    "PipelineRunnerService": _PIPELINE_RUNNER_SERVICE_MODULE,
    "QuarantineService": "bioetl.application.services.quarantine_service",
    "RunManifestDiffEntry": _RUN_MANIFEST_INSPECTION_SERVICE_MODULE,
    "RunManifestDiffResult": _RUN_MANIFEST_INSPECTION_SERVICE_MODULE,
    "RunManifestInspectionResult": _RUN_MANIFEST_INSPECTION_SERVICE_MODULE,
    "RunManifestInspectionService": _RUN_MANIFEST_INSPECTION_SERVICE_MODULE,
    "RunOptions": _PIPELINE_RUNNER_SERVICE_MODULE,
    "RunResult": _PIPELINE_RUNNER_SERVICE_MODULE,
    "TableInfo": _EXPORT_SERVICE_MODULE,
    "TablePreview": _EXPORT_SERVICE_MODULE,
    "TableVacuumResult": _VACUUM_SERVICE_MODULE,
    "VacuumAllResult": _VACUUM_SERVICE_MODULE,
    "VacuumService": _VACUUM_SERVICE_MODULE,
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
    "LineageNodeRelationResult",
    "LineageRunExplanationResult",
    "LineageTraceResult",
    "MetricsService",
    "ObservabilityWorkflowService",
    "PipelineNotFoundError",
    "PipelineRunLifecycleService",
    "PipelineRunResult",
    "PipelineRunnerService",
    "QuarantineService",
    "RunForensicDossierResult",
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
