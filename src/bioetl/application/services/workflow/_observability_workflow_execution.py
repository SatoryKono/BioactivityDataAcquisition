# Boundary object/payload typing residual at this module.
"""Execution helpers for observability workflow aggregation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.checkpoint.checkpoint_service import (
    CheckpointService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
    RunManifestInspectionService,
)
from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionResult,
    AuditInspectionService,
)
from bioetl.application.services.workflow._observability_workflow_models import (
    AuditRunWorkflowResult,
    CheckpointAuditWorkflowResult,
    RunForensicDossierResult,
)
from bioetl.application.services.workflow._observability_workflow_support import (
    build_next_steps,
    build_status_section,
    build_traceability_section,
    classify_evidence_status,
    resolve_checkpoint_for_run,
    resolve_lineage_for_run,
    resolve_pipeline_name,
    resolve_quarantine_summary_for_run,
    resolve_run_manifest,
    trace_links_enabled,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.quality.quarantine_service import QuarantineService
    from bioetl.domain.ports import TracingPort


async def inspect_audit_run(
    *,
    audit_service: AuditInspectionService,
    run_manifest_service: RunManifestInspectionService | None,
    run_id: str,
    limit: int,
) -> AuditRunWorkflowResult:
    """Return audit entries plus best-effort run-manifest context."""
    audit = await audit_service.inspect_run(run_id, limit=limit)
    run_manifest = resolve_run_manifest(run_manifest_service, run_id)
    return AuditRunWorkflowResult(
        run_id=run_id,
        audit=audit,
        run_manifest=run_manifest,
    )


async def inspect_run_dossier(
    *,
    audit_service: AuditInspectionService,
    checkpoint_service: CheckpointService,
    run_manifest_service: RunManifestInspectionService | None,
    lineage_service: LineageInspectionService | None,
    quarantine_service: QuarantineService | None,
    tracer: TracingPort | None,
    run_id: str,
    audit_limit: int,
    run_manifest: RunManifestInspectionResult | None = None,
) -> RunForensicDossierResult:
    """Return a bounded forensic dossier across observability seams."""
    audit = await audit_service.inspect_run(run_id, limit=audit_limit)
    if run_manifest is None:
        run_manifest = resolve_run_manifest(run_manifest_service, run_id)
    pipeline_name = resolve_pipeline_name(run_manifest)
    checkpoint = await resolve_checkpoint_for_run(
        checkpoint_service=checkpoint_service,
        run_id=run_id,
        pipeline_name=pipeline_name,
    )
    lineage = resolve_lineage_for_run(lineage_service, run_id)  # pyright: ignore[reportArgumentType]
    quarantine_summary = await resolve_quarantine_summary_for_run(
        quarantine_service=quarantine_service,
        run_id=run_id,
        pipeline_name=pipeline_name,
        run_manifest=run_manifest,
    )
    traceability = build_traceability_section(
        run_id=run_id,
        run_manifest=run_manifest,
        lineage=lineage,
        audit=audit,
        trace_links_enabled=trace_links_enabled(tracer),
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
    *,
    audit_service: AuditInspectionService,
    checkpoint_service: CheckpointService,
    run_manifest_service: RunManifestInspectionService | None,
    pipeline_name: str,
    run_id: str | None,
    manifest_id: str | None,
    audit_limit: int,
) -> CheckpointAuditWorkflowResult:
    """Return checkpoint state with related audit and manifest context."""
    if manifest_id is not None:
        checkpoint = await checkpoint_service.get_checkpoint_for_manifest_id(
            pipeline_name,
            manifest_id,
        )
    elif run_id is not None:
        checkpoint = await checkpoint_service.get_checkpoint_for_run(
            pipeline_name,
            run_id,
        )
    else:
        checkpoint = await checkpoint_service.get_checkpoint(pipeline_name)
    resolved_run_id = run_id or (checkpoint.run_id if checkpoint is not None else None)

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

    audit = await audit_service.inspect_run(
        resolved_run_id,
        limit=audit_limit,
    )
    run_manifest = resolve_run_manifest(
        run_manifest_service,
        resolved_run_id,
    )
    return CheckpointAuditWorkflowResult(
        pipeline_name=pipeline_name,
        checkpoint=checkpoint,
        audit=audit,
        run_manifest=run_manifest,
    )
