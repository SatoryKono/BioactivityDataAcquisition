"""Application workflows for operator-facing observability diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.observability.span_helpers import traced_async_operation
from bioetl.application.services._observability_workflow_support import (
    build_checkpoint_compatibility_section,
    build_next_steps,
    build_status_section,
    build_traceability_section,
    classify_evidence_status,
    enrich_quarantine_summary,
    resolve_checkpoint_for_run,
    resolve_lineage_for_run,
    resolve_pipeline_name,
    resolve_run_manifest,
    trace_links_enabled,
)
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
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
        LineageRunExplanationResult,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
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
            "compatibility": build_checkpoint_compatibility_section(
                checkpoint=self.checkpoint,
                run_manifest=self.run_manifest,
            ),
        }


@dataclass(frozen=True, slots=True)
class RunForensicDossierResult:
    """Bounded one-run dossier across observability and control-plane surfaces."""

    run_id: str
    pipeline_name: str | None
    audit: AuditInspectionResult
    run_manifest: RunManifestInspectionResult | None = None
    checkpoint: CheckpointInfo | None = None
    lineage: LineageRunExplanationResult | None = None
    quarantine_summary: dict[str, object] | None = None
    traceability: dict[str, object] | None = None
    status: dict[str, object] | None = None
    missing_evidence: tuple[str, ...] = ()
    degraded_evidence: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe dossier payload for CLI or API responses."""
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "audit": self.audit.to_dict(),
            "run_manifest": (
                self.run_manifest.to_dict() if self.run_manifest is not None else None
            ),
            "checkpoint": (
                {
                    "pipeline_name": self.checkpoint.pipeline_name,
                    "run_id": self.checkpoint.run_id,
                    "metadata": self.checkpoint.metadata,
                }
                if self.checkpoint is not None
                else None
            ),
            "lineage": self.lineage.to_dict() if self.lineage is not None else None,
            "quarantine_summary": self.quarantine_summary,
            "traceability": self.traceability,
            "status": self.status,
            "missing_evidence": list(self.missing_evidence),
            "degraded_evidence": list(self.degraded_evidence),
            "next_steps": list(self.next_steps),
        }


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
            return await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
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
            result = await self._inspect_audit_run_impl(run_id=run_id, limit=limit)
            span.set_attribute(_TRACE_ATTR_SUCCESS, True)
            span.set_attribute(
                _TRACE_ATTR_AUDIT_ENTRIES_COUNT, len(result.audit.entries)
            )
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
        run_manifest = resolve_run_manifest(self.run_manifest_service, run_id)
        return AuditRunWorkflowResult(
            run_id=run_id,
            audit=audit,
            run_manifest=run_manifest,
        )

    async def inspect_run_dossier(
        self,
        run_id: str,
        *,
        audit_limit: int = 100,
    ) -> RunForensicDossierResult:
        """Return a one-run dossier across audit, control-plane, and triage seams."""
        if self.tracer is None:
            return await self._inspect_run_dossier_impl(
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
            result = await self._inspect_run_dossier_impl(
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

    async def _inspect_run_dossier_impl(
        self,
        *,
        run_id: str,
        audit_limit: int,
    ) -> RunForensicDossierResult:
        """Implement dossier aggregation without tracing concerns."""
        audit = await self.audit_service.inspect_run(run_id, limit=audit_limit)
        run_manifest = resolve_run_manifest(self.run_manifest_service, run_id)
        pipeline_name = resolve_pipeline_name(run_manifest)
        checkpoint = await resolve_checkpoint_for_run(
            checkpoint_service=self.checkpoint_service,
            run_id=run_id,
            pipeline_name=pipeline_name,
        )
        lineage = resolve_lineage_for_run(self.lineage_service, run_id)
        quarantine_summary = await self._resolve_quarantine_summary_for_run(
            run_id=run_id,
            pipeline_name=pipeline_name,
            run_manifest=run_manifest,
        )
        traceability = build_traceability_section(
            run_id=run_id,
            run_manifest=run_manifest,
            lineage=lineage,
            audit=audit,
            trace_links_enabled=trace_links_enabled(self.tracer),
        )
        missing_evidence, degraded_evidence = classify_evidence_status(
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            traceability=traceability,
        )
        next_steps = build_next_steps(
            run_manifest=run_manifest,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
        )
        status = build_status_section(
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
        )
        return RunForensicDossierResult(
            run_id=run_id,
            pipeline_name=pipeline_name,
            audit=audit,
            run_manifest=run_manifest,
            checkpoint=checkpoint,
            lineage=lineage,
            quarantine_summary=quarantine_summary,
            traceability=traceability,
            status=status,
            missing_evidence=missing_evidence,
            degraded_evidence=degraded_evidence,
            next_steps=next_steps,
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
            return await self._inspect_checkpoint_workflow_impl(
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
            result = await self._inspect_checkpoint_workflow_impl(
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

    async def _inspect_checkpoint_workflow_impl(
        self,
        *,
        pipeline_name: str,
        run_id: str | None,
        manifest_id: str | None,
        audit_limit: int,
    ) -> CheckpointAuditWorkflowResult:
        """Implement checkpoint diagnostics workflow without tracing concerns."""
        if manifest_id is not None:
            checkpoint = await self.checkpoint_service.get_checkpoint_for_manifest_id(
                pipeline_name,
                manifest_id,
            )
        elif run_id is not None:
            checkpoint = await self.checkpoint_service.get_checkpoint_for_run(
                pipeline_name,
                run_id,
            )
        else:
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
        run_manifest = resolve_run_manifest(
            self.run_manifest_service,
            resolved_run_id,
        )
        return CheckpointAuditWorkflowResult(
            pipeline_name=pipeline_name,
            checkpoint=checkpoint,
            audit=audit,
            run_manifest=run_manifest,
        )

    async def _resolve_quarantine_summary_for_run(
        self,
        *,
        run_id: str,
        pipeline_name: str | None,
        run_manifest: RunManifestInspectionResult | None,
    ) -> dict[str, object] | None:
        """Resolve bounded quarantine summary for one run when available."""
        if self.quarantine_service is None or pipeline_name is None:
            return None
        try:
            stats = await self.quarantine_service.get_filtered_stats(
                pipeline=pipeline_name,
                run_id=run_id,
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        return self._enrich_quarantine_summary(
            stats=stats,
            run_id=run_id,
            run_manifest=run_manifest,
        )

    @staticmethod
    def _enrich_quarantine_summary(
        *,
        stats: dict[str, object],
        run_id: str,
        run_manifest: RunManifestInspectionResult | None,
    ) -> dict[str, object]:
        """Attach run-scoped metadata and Bronze denominator when available."""
        return enrich_quarantine_summary(
            stats=stats,
            run_id=run_id,
            run_manifest=run_manifest,
        )
