"""Application workflows for operator-facing observability diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.observability.tracing_operation_helpers import (
    traced_async_operation,
)
from bioetl.application.services.checkpoint.checkpoint_service import (
    CheckpointService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionService,
)
from bioetl.application.services.workflow._observability_workflow_execution import (
    inspect_audit_run as inspect_audit_run_impl,
)
from bioetl.application.services.workflow._observability_workflow_execution import (
    inspect_checkpoint_workflow as inspect_checkpoint_workflow_impl,
)
from bioetl.application.services.workflow._observability_workflow_execution import (
    inspect_run_dossier as inspect_run_dossier_impl,
)
from bioetl.application.services.workflow._observability_workflow_models import (
    AuditRunWorkflowResult,
    CheckpointAuditWorkflowResult,
    RunForensicDossierResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.domain.ports import TracingPort

__all__ = [
    "AuditRunWorkflowResult",
    "CheckpointAuditWorkflowResult",
    "ObservabilityWorkflowService",
    "RunForensicDossierResult",
]

_TRACE_ATTR_AUDIT_ENTRIES_COUNT = "bioetl.audit_entries_count"
_TRACE_ATTR_COMPONENT = "bioetl.component"
_TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE = "bioetl.has_run_manifest_service"
_TRACE_ATTR_OPERATION = "bioetl.operation"
_TRACE_ATTR_SUCCESS = "bioetl.success"


@dataclass(slots=True)
class ObservabilityWorkflowService:
    """Compose audit, checkpoint, and run-manifest diagnostics workflows."""

    audit_service: AuditInspectionService
    checkpoint_service: CheckpointService
    run_manifest_service: RunManifestInspectionService | None = None
    lineage_service: LineageInspectionService | None = None
    quarantine_service: QuarantineService | None = None
    tracer: TracingPort | None = None
    TRACER_NAME = "bioetl.diagnostics"

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditRunWorkflowResult:
        """Return audit entries and best-effort manifest context for one run."""
        if self.tracer is None:
            return await inspect_audit_run_impl(
                audit_service=self.audit_service,
                run_manifest_service=self.run_manifest_service,
                run_id=run_id,
                limit=limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_audit_run",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_audit_run",
                "bioetl.limit": limit,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await inspect_audit_run_impl(
                audit_service=self.audit_service,
                run_manifest_service=self.run_manifest_service,
                run_id=run_id,
                limit=limit,
            )
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result

    async def inspect_run_dossier(
        self,
        run_id: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Return a one-run dossier across audit, control-plane, and triage seams."""
        if self.tracer is None:
            return await inspect_run_dossier_impl(
                audit_service=self.audit_service,
                checkpoint_service=self.checkpoint_service,
                run_manifest_service=self.run_manifest_service,
                lineage_service=self.lineage_service,
                quarantine_service=self.quarantine_service,
                tracer=self.tracer,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_run_dossier",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_run_dossier",
                "bioetl.audit_limit": audit_limit,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
                "bioetl.has_lineage_service": self.lineage_service is not None,
                "bioetl.has_quarantine_service": self.quarantine_service is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await inspect_run_dossier_impl(
                audit_service=self.audit_service,
                checkpoint_service=self.checkpoint_service,
                run_manifest_service=self.run_manifest_service,
                lineage_service=self.lineage_service,
                quarantine_service=self.quarantine_service,
                tracer=self.tracer,
                run_id=run_id,
                audit_limit=audit_limit,
            )
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute(
                "bioetl.missing_evidence_count", len(result.missing_evidence)
            )
            span.set_attribute(
                "bioetl.degraded_evidence_count", len(result.degraded_evidence)
            )
            return result

    async def inspect_manifest_dossier(
        self,
        identifier: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Return a dossier by manifest_id or run_id through manifest inspection."""
        if self.run_manifest_service is None:
            raise ValueError("run manifest service is required for manifest dossier")
        run_manifest = self.run_manifest_service.show(identifier)
        return await inspect_run_dossier_impl(
            audit_service=self.audit_service,
            checkpoint_service=self.checkpoint_service,
            run_manifest_service=self.run_manifest_service,
            lineage_service=self.lineage_service,
            quarantine_service=self.quarantine_service,
            tracer=self.tracer,
            run_id=str(run_manifest.manifest.run_id),
            audit_limit=audit_limit,
            run_manifest=run_manifest,
        )

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        manifest_id: str | None = None,
        audit_limit: int = 100,
    ) -> CheckpointAuditWorkflowResult:
        """Return checkpoint state and any related audit/run-manifest context."""
        if run_id is not None and manifest_id is not None:
            raise ValueError(
                "checkpoint diagnostics accept either run_id or manifest_id, not both"
            )
        if self.tracer is None:
            return await inspect_checkpoint_workflow_impl(
                audit_service=self.audit_service,
                checkpoint_service=self.checkpoint_service,
                run_manifest_service=self.run_manifest_service,
                pipeline_name=pipeline_name,
                run_id=run_id,
                manifest_id=manifest_id,
                audit_limit=audit_limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_checkpoint_workflow",
            {
                _TRACE_ATTR_COMPONENT: "observability_workflow_service",
                _TRACE_ATTR_OPERATION: "inspect_checkpoint_workflow",
                "bioetl.pipeline": pipeline_name,
                "bioetl.audit_limit": audit_limit,
                "bioetl.has_explicit_run_id": run_id is not None,
                "bioetl.has_explicit_manifest_id": manifest_id is not None,
                _TRACE_ATTR_HAS_RUN_MANIFEST_SERVICE: self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await inspect_checkpoint_workflow_impl(
                audit_service=self.audit_service,
                checkpoint_service=self.checkpoint_service,
                run_manifest_service=self.run_manifest_service,
                pipeline_name=pipeline_name,
                run_id=run_id,
                manifest_id=manifest_id,
                audit_limit=audit_limit,
            )
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
            span.set_attribute("bioetl.has_checkpoint", result.checkpoint is not None)
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result
