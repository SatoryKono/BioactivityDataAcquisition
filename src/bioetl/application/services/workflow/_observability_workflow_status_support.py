"""Status section helpers for observability workflow dossiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)
from bioetl.application.services.workflow._observability_workflow_evidence_support import (
    resolve_required_evidence_profile,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )

_CRITICAL_EVIDENCE_PROFILES = frozenset({"forensic_grade"})


def build_status_section(
    *,
    run_manifest: RunManifestInspectionResult | None,
    checkpoint: CheckpointInfo | None,
    lineage: LineageRunExplanationResult | None,
    quarantine_summary: dict[str, object] | None,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> dict[str, object]:
    diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
    persistence_profile = diagnostics.get("persistence_profile")
    attained_profile = (
        persistence_profile.get("attained_profile")
        if isinstance(persistence_profile, dict)
        else None
    )
    operational_success_criteria = build_operational_success_criteria(
        diagnostics=diagnostics,
        attained_profile=attained_profile,
        missing_evidence=missing_evidence,
        degraded_evidence=degraded_evidence,
    )
    return {
        "forensic_profile": attained_profile,
        "latest_status": diagnostics.get("latest_status"),
        "latest_event_type": diagnostics.get("latest_event_type"),
        "checkpoint_status": (
            "missing"
            if checkpoint is None
            else checkpoint.metadata.get("status", "present")
        ),
        "lineage_status": "present" if lineage is not None else "missing",
        "quarantine_status": (
            "present" if quarantine_summary is not None else "missing"
        ),
        "missing_evidence_count": len(missing_evidence),
        "degraded_evidence_count": len(degraded_evidence),
        "operational_success": operational_success_criteria["operational_success"],
        "operational_success_criteria": operational_success_criteria,
    }


def build_operational_success_criteria(
    *,
    diagnostics: dict[str, object],
    attained_profile: object,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> dict[str, object]:
    """Build dossier-backed success criteria for operator decisions."""
    required_profile = resolve_required_evidence_profile(diagnostics)
    critical_pipeline = (
        diagnostics.get("critical_pipeline") is True
        or required_profile in _CRITICAL_EVIDENCE_PROFILES
    )
    persistence_profile = diagnostics.get("persistence_profile")
    required_profile_satisfied = True
    if isinstance(persistence_profile, dict) and isinstance(
        persistence_profile.get("required_profile_satisfied"), bool
    ):
        required_profile_satisfied = bool(
            persistence_profile["required_profile_satisfied"]
        )
    runtime_terminal_success = diagnostics.get("latest_status") == "success"
    dossier_evidence_satisfied = (
        required_profile_satisfied and not missing_evidence and not degraded_evidence
    )
    operational_success = runtime_terminal_success and (
        dossier_evidence_satisfied if critical_pipeline else True
    )
    return {
        "critical_pipeline": critical_pipeline,
        "runtime_terminal_success": runtime_terminal_success,
        "required_evidence_profile": required_profile,
        "attained_evidence_profile": attained_profile,
        "required_profile_satisfied": required_profile_satisfied,
        "dossier_evidence_satisfied": dossier_evidence_satisfied,
        "operational_success": operational_success,
    }
