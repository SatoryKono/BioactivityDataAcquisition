"""Operator-facing audit and checkpoint diagnostics workflows."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.audit_inspection_service import (
    AuditInspectionResult,
    AuditInspectionService,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionResult,
    RunManifestInspectionService,
)

__all__ = [
    "AuditRunWorkflowResult",
    "CheckpointAuditWorkflowResult",
    "ObservabilityWorkflowService",
]


@dataclass(frozen=True, slots=True)
class AuditRunWorkflowResult:
    """Operator-facing audit inspection workflow payload for one run."""

    run_id: str
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe workflow payload."""
        return {
            "run_id": self.run_id,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class CheckpointAuditWorkflowResult:
    """Operator-facing checkpoint + audit workflow payload for one pipeline."""

    pipeline_name: str
    checkpoint: CheckpointInfo | None
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON/YAML-safe workflow payload."""
        return {
            "pipeline_name": self.pipeline_name,
            "checkpoint": (
                {
                    "pipeline_name": self.checkpoint.pipeline_name,
                    "run_id": self.checkpoint.run_id,
                    "metadata": self.checkpoint.metadata,
                }
                if self.checkpoint is not None
                else None
            ),
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(slots=True)
class ObservabilityWorkflowService:
    """Assemble higher-level operator diagnostics workflows."""

    audit_service: AuditInspectionService
    checkpoint_service: CheckpointService
    run_manifest_service: RunManifestInspectionService | None = None

    async def inspect_audit_run(
        self,
        run_id: str,
        *,
        limit: int = 100,
    ) -> AuditRunWorkflowResult:
        """Return one operator-friendly audit workflow for a pipeline run."""
        audit = await self.audit_service.inspect_run(run_id, limit=limit)
        run_manifest = self._resolve_run_manifest(run_id)
        return AuditRunWorkflowResult(
            run_id=run_id,
            audit=audit,
            run_manifest=run_manifest,
        )

    async def inspect_checkpoint_workflow(
        self,
        pipeline_name: str,
        *,
        run_id: str | None = None,
        audit_limit: int = 100,
    ) -> CheckpointAuditWorkflowResult:
        """Return one operator-friendly checkpoint inspection workflow."""
        checkpoint = await self.checkpoint_service.get_checkpoint(pipeline_name)
        resolved_run_id = run_id
        if resolved_run_id is None and checkpoint is not None:
            resolved_run_id = checkpoint.run_id

        if resolved_run_id is None:
            audit = AuditInspectionResult(
                query={"run_id": None, "limit": audit_limit},
                entries=(),
            )
            run_manifest = None
        else:
            audit = await self.audit_service.inspect_run(
                resolved_run_id,
                limit=audit_limit,
            )
            run_manifest = self._resolve_run_manifest(resolved_run_id)

        return CheckpointAuditWorkflowResult(
            pipeline_name=pipeline_name,
            checkpoint=checkpoint,
            audit=audit,
            run_manifest=run_manifest,
        )

    def _resolve_run_manifest(
        self,
        run_id: str,
    ) -> RunManifestInspectionResult | None:
        """Best-effort manifest lookup for operator diagnostics workflows."""
        if self.run_manifest_service is None:
            return None
        try:
            return self.run_manifest_service.show(run_id)
        except ValueError:
            return None
