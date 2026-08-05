"""Evidence classification helpers for observability workflow dossiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )

_CRITICAL_EVIDENCE_PROFILES = frozenset({"forensic_grade"})


def classify_evidence_status(
    *,
    run_manifest: RunManifestInspectionResult | None,
    checkpoint: CheckpointInfo | None,
    lineage: LineageRunExplanationResult | None,
    quarantine_summary: dict[str, object] | None,
    traceability: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing = ["run_manifest"] if run_manifest is None else []
    degraded = classify_checkpoint_status(checkpoint)
    if lineage is None:
        degraded.append("lineage")
    if quarantine_summary is None:
        degraded.append("quarantine_summary")
    degraded.extend(collect_traceability_degradation(traceability))
    if requires_critical_dossier_evidence(run_manifest) and (missing or degraded):
        degraded.append("critical_dossier_evidence_gap")
    return tuple(missing), tuple(degraded)


def requires_critical_dossier_evidence(
    run_manifest: RunManifestInspectionResult | None,
) -> bool:
    """Return whether this run requires forensic-grade dossier evidence."""
    if run_manifest is None:
        return False
    diagnostics = run_manifest.diagnostics
    if diagnostics.get("critical_pipeline") is True:
        return True
    return resolve_required_evidence_profile(diagnostics) in _CRITICAL_EVIDENCE_PROFILES


def resolve_required_evidence_profile(diagnostics: dict[str, object]) -> str | None:
    """Resolve the evidence profile required by runtime/control-plane policy."""
    persistence_profile = diagnostics.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        required_profile = persistence_profile.get("required_profile")
        if isinstance(required_profile, str) and required_profile:
            return required_profile
    required_profile = diagnostics.get("required_persistence_profile")
    if isinstance(required_profile, str) and required_profile:
        return required_profile
    return None


def classify_checkpoint_status(checkpoint: CheckpointInfo | None) -> list[str]:
    if checkpoint is None:
        return ["checkpoint"]
    if checkpoint.metadata.get("status") == "mismatched_run_context":
        return ["checkpoint_mismatched_run"]
    return []


def collect_traceability_degradation(traceability: dict[str, object]) -> list[str]:
    degraded: list[str] = []
    persistence_profile = traceability.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        degraded.extend(collect_persistence_profile_degradation(persistence_profile))
    if has_correlation_anchor_gaps(traceability):
        degraded.append("correlation_anchor_gaps")
    if has_composite_correlation_policy_gap(traceability):
        degraded.append("composite_correlation_policy_gap")
    if not traceability.get("trace_links_available", False):
        degraded.append("trace_links_unavailable")
    return degraded


def collect_persistence_profile_degradation(
    persistence_profile: dict[str, object],
) -> list[str]:
    degraded: list[str] = []
    attained = persistence_profile.get("attained_profile")
    if attained not in {None, "forensic_grade"}:
        degraded.append(f"persistence_profile:{attained}")
    for key in (
        "required_profile_missing_requirements",
        "replay_ready_missing_requirements",
        "forensic_grade_missing_requirements",
    ):
        value = persistence_profile.get(key)
        if isinstance(value, list) and value:
            degraded.append(key)
    return degraded


def has_correlation_anchor_gaps(traceability: dict[str, object]) -> bool:
    correlation_gaps = traceability.get("correlation_anchor_gaps")
    return isinstance(correlation_gaps, dict) and any(
        isinstance(value, int) and value > 0 for value in correlation_gaps.values()
    )


def has_composite_correlation_policy_gap(traceability: dict[str, object]) -> bool:
    composite_projection = traceability.get("composite_projection")
    if not isinstance(composite_projection, dict):
        return False
    if composite_projection.get("composite_run_id_consistent") is False:
        return True
    correlation_policy = composite_projection.get("correlation_policy")
    return isinstance(correlation_policy, dict) and correlation_policy.get(
        "status"
    ) not in {None, "satisfied"}
