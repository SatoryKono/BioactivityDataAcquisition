"""Result payload models for observability workflow services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.audit_inspection_service import (
    AuditInspectionResult,
)
from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )

__all__ = [
    "AuditRunWorkflowResult",
    "CheckpointAuditWorkflowResult",
    "RunForensicDossierResult",
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
        from bioetl.application.services._observability_workflow_support import (
            build_checkpoint_compatibility_section,
        )

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
        lineage = self.lineage
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
            "lineage": lineage.to_dict() if lineage is not None else None,
            "quarantine_summary": self.quarantine_summary,
            "traceability": self.traceability,
            "status": self.status,
            "missing_evidence": list(self.missing_evidence),
            "degraded_evidence": list(self.degraded_evidence),
            "next_steps": list(self.next_steps),
        }
