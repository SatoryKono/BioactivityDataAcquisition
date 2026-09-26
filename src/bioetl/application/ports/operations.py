"""Operator-facing application service ports (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.application.services.checkpoint.checkpoint_models import (
        CheckpointInfo,
    )
    from bioetl.application.services.contracts.contract_migration_models import (
        ContractMigrationPlanSummary,
    )
    from bioetl.application.services.export_lineage.audit_inspection_service import (
        AuditInspectionResult,
    )
    from bioetl.application.services.export_lineage.export_models import (
        ExportOptions,
        ExportResult,
        TableInfo,
        TablePreview,
    )
    from bioetl.application.services.ops.config_service import (
        PipelineInfo,
        SettingsInfo,
    )
    from bioetl.application.services.ops.lock_service import LockInfo
    from bioetl.application.services.ops.vacuum_service import (
        TableVacuumResult,
        VacuumAllResult,
    )
    from bioetl.application.services.workflow.observability_workflow_service import (
        AuditRunWorkflowResult,
        CheckpointAuditWorkflowResult,
        RunForensicDossierResult,
    )
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.ports import AuditLayer
    from bioetl.domain.types import JsonDict, RunID


class CheckpointServiceProtocol(Protocol):
    """Checkpoint administration used by operator-facing interfaces."""

    async def list_checkpoints(self) -> list[CheckpointInfo]:
        """List stored pipeline checkpoints."""
        ...

    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None:
        """Return the latest checkpoint for a pipeline, if any."""
        ...

    async def get_checkpoint_for_run(
        self,
        pipeline_name: str,
        run_id: str,
    ) -> CheckpointInfo | None:
        """Return the checkpoint bound to a run id, if any."""
        ...

    async def get_checkpoint_for_manifest_id(
        self,
        pipeline_name: str,
        manifest_id: str,
    ) -> CheckpointInfo | None:
        """Return the checkpoint bound to a manifest id, if any."""
        ...

    async def delete_checkpoint(self, pipeline_name: str) -> bool:
        """Delete the stored checkpoint for a pipeline."""
        ...

    async def aclose(self) -> None:
        """Release resources held by the service."""
        ...


class AuditInspectionServiceProtocol(Protocol):
    """Read-only audit inspection used by operator diagnostics."""

    async def list_entries(
        self,
        *,
        run_id: str | None = None,
        layer: AuditLayer | str | None = None,
        table_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """List audit entries matching the supplied filters."""
        ...

    async def inspect_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Inspect audit history for one run."""
        ...

    async def inspect_table(
        self,
        table_name: str,
        *,
        layer: AuditLayer | str | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult:
        """Inspect audit history for one table."""
        ...

    async def aclose(self) -> None:
        """Release resources held by the service."""
        ...


class VacuumServiceProtocol(Protocol):
    """Batch vacuum operations exposed to maintenance interfaces."""

    def collect_tables(self, layer: str = "all") -> list[tuple[str, str]]:
        """Collect (layer, table) pairs eligible for vacuum."""
        ...

    async def vacuum_table(
        self,
        table_name: str,
        layer: str,
        retention_days: int,
        dry_run: bool,
    ) -> TableVacuumResult:
        """Vacuum one table under the given retention policy."""
        ...

    async def vacuum_all(
        self,
        tables: list[tuple[str, str]],
        retention_days: int,
        dry_run: bool,
    ) -> VacuumAllResult:
        """Vacuum every collected table under the given retention policy."""
        ...


class ContractMigrationServiceProtocol(Protocol):
    """Planner-only contract migration operations."""

    def plan_pipeline(self, pipeline_name: str) -> ContractMigrationPlanSummary:
        """Build a contract-migration plan for one pipeline."""
        ...


class ObservabilityWorkflowServiceProtocol(Protocol):
    """Cross-service operator diagnostics workflows."""

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditRunWorkflowResult:
        """Run the audit-inspection operator workflow for one run."""
        ...

    async def inspect_run_dossier(
        self,
        run_id: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Build a forensic dossier for one run id."""
        ...

    async def inspect_manifest_dossier(
        self,
        identifier: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Build a forensic dossier for one manifest identifier."""
        ...

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        manifest_id: str | None = None,
        audit_limit: int = 100,
    ) -> CheckpointAuditWorkflowResult:
        """Run checkpoint-plus-audit inspection for one pipeline."""
        ...


class ConfigServiceProtocol(Protocol):
    """Administrative configuration access operations."""

    def get_settings(self) -> SettingsInfo:
        """Return the active administrative settings snapshot."""
        ...

    def load_pipeline_config(self, pipeline_name: str) -> PipelineConfig:
        """Load the typed pipeline configuration."""
        ...

    def get_pipeline_yaml_config(self, pipeline_name: str) -> JsonDict:
        """Return the raw YAML pipeline configuration."""
        ...

    def validate_pipeline_config(self, pipeline_name: str) -> PipelineInfo:
        """Validate one pipeline configuration and return info."""
        ...

    def list_pipelines(self) -> list[str]:
        """List registered pipeline names."""
        ...

    def get_dq_config(self, pipeline_name: str) -> JsonDict:
        """Return the DQ configuration for one pipeline."""
        ...

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool:
        """Validate a DQ configuration payload."""
        ...

    def get_effective_config_artifact(
        self,
        pipeline_name: str,
        runtime_overrides: JsonDict | None = None,
    ) -> JsonDict:
        """Build the effective configuration artifact for one pipeline."""
        ...

    def check_config_compatibility(
        self,
        artifact1: JsonDict,
        artifact2: JsonDict,
    ) -> bool:
        """Return whether two effective-config artifacts are compatible."""
        ...


class ExportServiceProtocol(Protocol):
    """Delta export and preview operations."""

    def list_tables(self, layer: str = "all") -> list[TableInfo]:
        """List exportable tables for the requested layer."""
        ...

    async def preview(
        self,
        table_name: str,
        layer: str = "silver",
        sample_rows: int = 5,
    ) -> TablePreview:
        """Preview sample rows from one table."""
        ...

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Export one table according to the supplied options."""
        ...


class LockServiceProtocol(Protocol):
    """Administrative lock inspection and release operations."""

    async def check_lock(self, pipeline_id: str, owner_id: RunID) -> bool:
        """Return whether the owner currently holds the pipeline lock."""
        ...

    async def release_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock held by the given owner."""
        ...

    async def force_release_all(
        self,
        owner_id: RunID,
        pipeline_ids: list[str],
    ) -> list[str]:
        """Force-release locks for the given owner and pipelines."""
        ...

    async def list_locks(self) -> list[LockInfo]:
        """List currently held administrative locks."""
        ...

    async def aclose(self) -> None:
        """Release resources held by the service."""
        ...
