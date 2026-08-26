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

    async def list_checkpoints(self) -> list[CheckpointInfo]: ...

    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None: ...

    async def get_checkpoint_for_run(
        self,
        pipeline_name: str,
        run_id: str,
    ) -> CheckpointInfo | None: ...

    async def get_checkpoint_for_manifest_id(
        self,
        pipeline_name: str,
        manifest_id: str,
    ) -> CheckpointInfo | None: ...

    async def delete_checkpoint(self, pipeline_name: str) -> bool: ...

    async def aclose(self) -> None: ...


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
    ) -> AuditInspectionResult: ...

    async def inspect_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditInspectionResult: ...

    async def inspect_table(
        self,
        table_name: str,
        *,
        layer: AuditLayer | str | None = None,
        limit: int = 100,
    ) -> AuditInspectionResult: ...

    async def aclose(self) -> None: ...


class VacuumServiceProtocol(Protocol):
    """Batch vacuum operations exposed to maintenance interfaces."""

    def collect_tables(self, layer: str = "all") -> list[tuple[str, str]]: ...

    async def vacuum_table(
        self,
        table_name: str,
        layer: str,
        retention_days: int,
        dry_run: bool,
    ) -> TableVacuumResult: ...

    async def vacuum_all(
        self,
        tables: list[tuple[str, str]],
        retention_days: int,
        dry_run: bool,
    ) -> VacuumAllResult: ...


class ContractMigrationServiceProtocol(Protocol):
    """Planner-only contract migration operations."""

    def plan_pipeline(self, pipeline_name: str) -> ContractMigrationPlanSummary: ...


class ObservabilityWorkflowServiceProtocol(Protocol):
    """Cross-service operator diagnostics workflows."""

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditRunWorkflowResult: ...

    async def inspect_run_dossier(
        self,
        run_id: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult: ...

    async def inspect_manifest_dossier(
        self,
        identifier: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult: ...

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        manifest_id: str | None = None,
        audit_limit: int = 100,
    ) -> CheckpointAuditWorkflowResult: ...


class ConfigServiceProtocol(Protocol):
    """Administrative configuration access operations."""

    def get_settings(self) -> SettingsInfo: ...

    def load_pipeline_config(self, pipeline_name: str) -> PipelineConfig: ...

    def get_pipeline_yaml_config(self, pipeline_name: str) -> JsonDict: ...

    def validate_pipeline_config(self, pipeline_name: str) -> PipelineInfo: ...

    def list_pipelines(self) -> list[str]: ...

    def get_dq_config(self, pipeline_name: str) -> JsonDict: ...

    def validate_dq_config(self, pipeline_name: str, dq_config: JsonDict) -> bool: ...

    def get_effective_config_artifact(
        self,
        pipeline_name: str,
        runtime_overrides: JsonDict | None = None,
    ) -> JsonDict: ...

    def check_config_compatibility(
        self,
        artifact1: JsonDict,
        artifact2: JsonDict,
    ) -> bool: ...


class ExportServiceProtocol(Protocol):
    """Delta export and preview operations."""

    def list_tables(self, layer: str = "all") -> list[TableInfo]: ...

    async def preview(
        self,
        table_name: str,
        layer: str = "silver",
        sample_rows: int = 5,
    ) -> TablePreview: ...

    async def export(
        self,
        table_name: str,
        layer: str = "silver",
        options: ExportOptions | None = None,
    ) -> ExportResult: ...


class LockServiceProtocol(Protocol):
    """Administrative lock inspection and release operations."""

    async def check_lock(self, pipeline_id: str, owner_id: RunID) -> bool: ...

    async def release_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool: ...

    async def force_release_all(
        self,
        owner_id: RunID,
        pipeline_ids: list[str],
    ) -> list[str]: ...

    async def list_locks(self) -> list[LockInfo]: ...

    async def aclose(self) -> None: ...
