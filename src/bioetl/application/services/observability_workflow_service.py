"""Application workflows for operator-facing observability diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.observability.span_helpers import traced_async_operation
from bioetl.application.services.audit_inspection_service import (
    AuditInspectionResult,
    AuditInspectionService,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
    RunManifestInspectionService,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import TracingPort

__all__ = [
    "AuditRunWorkflowResult",
    "CheckpointAuditWorkflowResult",
    "ObservabilityWorkflowService",
]


@dataclass(frozen=True, slots=True)
class AuditRunWorkflowResult:
    """Aggregate operator view for one run's audit context."""

    run_id: str
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for CLI or API responses."""
        return {
            "run_id": self.run_id,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(frozen=True, slots=True)
class CheckpointAuditWorkflowResult:
    """Aggregate operator view for one checkpoint and related audit context."""

    pipeline_name: str
    checkpoint: CheckpointInfo | None
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation for CLI or API responses."""
        return {
            "pipeline_name": self.pipeline_name,
            "checkpoint": self.checkpoint,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
        }


@dataclass(slots=True)
class ObservabilityWorkflowService:
    """Compose audit, checkpoint, and run-manifest diagnostics workflows."""

    audit_service: AuditInspectionService
    checkpoint_service: CheckpointService
    run_manifest_service: RunManifestInspectionService | None = None
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
            return await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_audit_run",
            {
                "bioetl.component": "observability_workflow_service",
                "bioetl.operation": "inspect_audit_run",
                "bioetl.limit": limit,
                "bioetl.has_run_manifest_service": self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
            span.set_attribute("bioetl.success", True)
            span.set_attribute("bioetl.audit_entries_count", len(result.audit.entries))
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result

    async def _inspect_audit_run_impl(
        self,
        *,
        run_id: str,
        limit: int,
    ) -> AuditRunWorkflowResult:
        """Implement audit-run diagnostics without tracing concerns."""
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
        """Return checkpoint state and any related audit/run-manifest context."""
        if self.tracer is None:
            return await self._inspect_checkpoint_workflow_impl(
                pipeline_name=pipeline_name,
                run_id=run_id,
                audit_limit=audit_limit,
            )
        async with traced_async_operation(
            self.tracer,
            "diagnostics.inspect_checkpoint_workflow",
            {
                "bioetl.component": "observability_workflow_service",
                "bioetl.operation": "inspect_checkpoint_workflow",
                "bioetl.pipeline": pipeline_name,
                "bioetl.audit_limit": audit_limit,
                "bioetl.has_explicit_run_id": run_id is not None,
                "bioetl.has_run_manifest_service": self.run_manifest_service
                is not None,
            },
            tracer_name=self.TRACER_NAME,
        ) as span:
            result = await self._inspect_checkpoint_workflow_impl(
                pipeline_name=pipeline_name,
                run_id=run_id,
                audit_limit=audit_limit,
            )
            span.set_attribute("bioetl.success", True)
            span.set_attribute("bioetl.audit_entries_count", len(result.audit.entries))
            span.set_attribute("bioetl.has_checkpoint", result.checkpoint is not None)
            span.set_attribute(
                "bioetl.has_run_manifest", result.run_manifest is not None
            )
            return result

    async def _inspect_checkpoint_workflow_impl(
        self,
        *,
        pipeline_name: str,
        run_id: str | None,
        audit_limit: int,
    ) -> CheckpointAuditWorkflowResult:
        """Implement checkpoint diagnostics workflow without tracing concerns."""
        checkpoint = await self.checkpoint_service.get_checkpoint(pipeline_name)
        resolved_run_id = run_id or (
            checkpoint.run_id if checkpoint is not None else None
        )

        if resolved_run_id is None:
            audit = AuditInspectionResult(
                query={
                    "run_id": None,
                    "pipeline_name": pipeline_name,
                    "limit": audit_limit,
                },
                entries=(),
            )
            return CheckpointAuditWorkflowResult(
                pipeline_name=pipeline_name,
                checkpoint=checkpoint,
                audit=audit,
                run_manifest=None,
            )

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
        identifier: str,
    ) -> RunManifestInspectionResult | None:
        """Resolve manifest context best-effort without failing the workflow."""
        if self.run_manifest_service is None:
            return None
        try:
            return self.run_manifest_service.show(identifier)
        except ValueError:
            return None
