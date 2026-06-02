"""Legacy public services umbrella over specialized composition facades."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._lazy_exports import install_lazy_exports

if TYPE_CHECKING:

    async def cleanup_bronze(
        retention_days: int = 90,
        dry_run: bool = False,
    ) -> "BronzeCleanupResult": ...

    def get_adr_service() -> "AuditInspectionService": ...

    def get_audit_service() -> "AuditInspectionService": ...

    def get_bronze_cleanup_service() -> "BronzeCleanupService": ...

    def get_checkpoint_service() -> "CheckpointService": ...

    def get_config_service() -> "ConfigService": ...

    def get_contract_migration_service() -> "ContractMigrationService": ...

    def get_export_service() -> "ExportService": ...

    def get_forensic_run_diff_service() -> "ForensicRunDiffService": ...

    def get_health_server_dependencies() -> "HealthServerDependencies": ...

    def get_health_service() -> "HealthService": ...

    def get_lineage_service() -> "LineageInspectionService": ...

    def get_lock_service() -> "LockService": ...

    def get_metrics_service() -> "MetricsService": ...

    def get_observability_workflow_service() -> "ObservabilityWorkflowService": ...

    def get_pipeline_runner_service(
        registry: "PipelineRegistry | None" = None,
    ) -> "PipelineRunnerService": ...

    def get_quarantine_port() -> "QuarantinePort": ...

    def get_quarantine_service() -> "QuarantineService": ...

    def get_run_manifest_service() -> "RunManifestInspectionService": ...

    def get_vacuum_service() -> "VacuumService": ...

    def get_workflow_execution_service(
        registry: "PipelineRegistry | None" = None,
    ) -> "WorkflowExecutionService": ...

    def get_workflow_inspection_service() -> "WorkflowInspectionService": ...

    def get_workflow_runner_service(
        registry: "PipelineRegistry | None" = None,
    ) -> "WorkflowRunnerService": ...

    def load_workflow_config(name: str) -> "WorkflowConfig": ...


__all__ = [
    "cleanup_bronze",
    "get_adr_service",
    "get_audit_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_service",
    "get_config_service",
    "get_contract_migration_service",
    "get_export_service",
    "get_forensic_run_diff_service",
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
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
]

_PUBLIC_EXPORTS = {
    "cleanup_bronze": "bioetl.composition.maintenance_api",
    "get_adr_service": "bioetl.composition.control_plane_api",
    "get_audit_service": "bioetl.composition.observability_api",
    "get_bronze_cleanup_service": "bioetl.composition.maintenance_api",
    "get_checkpoint_service": "bioetl.composition.observability_api",
    "get_config_service": "bioetl.composition.control_plane_api",
    "get_contract_migration_service": "bioetl.composition.maintenance_api",
    "get_export_service": "bioetl.composition.control_plane_api",
    "get_forensic_run_diff_service": "bioetl.composition.control_plane_api",
    "get_health_server_dependencies": "bioetl.composition.health_api",
    "get_health_service": "bioetl.composition.health_api",
    "get_lineage_service": "bioetl.composition.control_plane_api",
    "get_lock_service": "bioetl.composition.control_plane_api",
    "get_metrics_service": "bioetl.composition.observability_api",
    "get_observability_workflow_service": "bioetl.composition.observability_api",
    "get_pipeline_runner_service": "bioetl.composition.execution_api",
    "get_quarantine_port": "bioetl.composition.health_api",
    "get_quarantine_service": "bioetl.composition.health_api",
    "get_run_manifest_service": "bioetl.composition.control_plane_api",
    "get_vacuum_service": "bioetl.composition.maintenance_api",
    "get_workflow_execution_service": "bioetl.composition.control_plane_api",
    "get_workflow_inspection_service": "bioetl.composition.control_plane_api",
    "get_workflow_runner_service": "bioetl.composition.control_plane_api",
    "load_workflow_config": "bioetl.composition.control_plane_api",
}
install_lazy_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
)
