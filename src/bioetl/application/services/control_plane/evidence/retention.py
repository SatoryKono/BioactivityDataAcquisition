"""Retention and reproducibility evidence-floor compliance helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from bioetl.application.services.control_plane.evidence.models import EvidenceCheck
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunManifest,
)


class ControlPlaneLifecyclePlanner(Protocol):
    """Read-only planner seam required by control-plane evidence."""

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool = True,
    ) -> ControlPlaneArtifactLifecyclePlan: ...


def build_retention_checks(
    *,
    manifest: RunManifest,
    plan: ControlPlaneArtifactLifecyclePlan,
) -> tuple[tuple[EvidenceCheck, ...], tuple[ControlPlaneArtifactRef, ...]]:
    """Classify lifecycle-plan evidence for one manifest without applying it."""
    relevant = tuple(
        artifact
        for artifact in plan.artifacts
        if _artifact_matches_manifest(artifact, manifest)
    )
    delete_candidates = tuple(
        artifact
        for artifact in relevant
        if artifact.decision is ControlPlaneArtifactLifecycleDecision.DELETE
    )
    required_profile = str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    ).strip()
    floor_required = required_profile in {"replay_ready", "forensic_grade"}
    evidence_floor_protected = any(
        reason.startswith("evidence_floor:")
        for artifact in relevant
        for reason in artifact.protected_by
    )
    present_surfaces = {artifact.surface for artifact in relevant}
    required_surfaces = {
        ControlPlaneArtifactSurface.RUN_MANIFEST,
        ControlPlaneArtifactSurface.RUN_LEDGER,
    }
    if floor_required:
        required_surfaces.update(
            {
                ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
                ControlPlaneArtifactSurface.LINEAGE,
            }
        )
    missing_surfaces = sorted(
        surface.value for surface in required_surfaces - present_surfaces
    )
    return (
        (
            EvidenceCheck(
                "retention_policy",
                "ERROR" if delete_candidates else "OK",
                (
                    "retention_delete_candidates_present"
                    if delete_candidates
                    else "retention_policy_satisfied"
                ),
                (
                    f"{len(delete_candidates)} selected-run artifacts are delete candidates."
                    if delete_candidates
                    else "Selected-run artifacts are retained by the current dry-run policy."
                ),
            ),
            EvidenceCheck(
                "evidence_floor",
                (
                    "OK"
                    if not floor_required or evidence_floor_protected
                    else "ERROR"
                ),
                (
                    "reproducibility_evidence_floor_satisfied"
                    if not floor_required or evidence_floor_protected
                    else "reproducibility_evidence_floor_unprotected"
                ),
                (
                    f"The {required_profile} evidence floor is protected."
                    if floor_required and evidence_floor_protected
                    else (
                        "No strict replay evidence floor is declared for this run."
                        if not floor_required
                        else f"The {required_profile} evidence floor lacks planner protection."
                    )
                ),
            ),
            EvidenceCheck(
                "required_evidence",
                "ERROR" if missing_surfaces else "OK",
                (
                    "required_evidence_surfaces_missing"
                    if missing_surfaces
                    else "required_evidence_surfaces_present"
                ),
                (
                    "Missing lifecycle evidence surfaces: " + ", ".join(missing_surfaces)
                    if missing_surfaces
                    else "Required lifecycle evidence surfaces are represented in the plan."
                ),
            ),
            EvidenceCheck(
                "archive",
                "UNKNOWN",
                "archive_evidence_not_recorded",
                "The local lifecycle plan does not attest external archive availability.",
            ),
        ),
        relevant,
    )


def _artifact_matches_manifest(
    artifact: ControlPlaneArtifactRef,
    manifest: RunManifest,
) -> bool:
    anchors = (f"manifest:{manifest.manifest_id}", f"run:{manifest.run_id}")
    if artifact.artifact_id in {manifest.manifest_id, str(manifest.run_id)}:
        return True
    if any(
        reason == anchor or reason.endswith(f":{anchor}")
        for reason in artifact.protected_by
        for anchor in anchors
    ):
        return True
    effective_config_id = manifest.code_provenance.effective_config_artifact_id
    if effective_config_id and artifact.artifact_id == effective_config_id:
        return True
    return artifact.artifact_id in _manifest_snapshot_ids(manifest)


def _manifest_snapshot_ids(manifest: RunManifest) -> set[str]:
    return {
        snapshot.snapshot_id
        for source in manifest.source_refs
        for snapshot in source.input_snapshots
    }


def summarize_retention_artifacts(
    artifacts: Iterable[ControlPlaneArtifactRef],
) -> list[dict[str, object]]:
    """Return bounded surface/reason counts without exposing filesystem paths."""
    counts: dict[tuple[str, str, str], int] = {}
    for artifact in artifacts:
        key = (
            artifact.surface.value,
            artifact.decision.value,
            artifact.reason,
        )
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "surface": surface,
            "decision": decision,
            "reason": reason,
            "count": count,
        }
        for (surface, decision, reason), count in sorted(counts.items())
    ]


__all__ = [
    "ControlPlaneLifecyclePlanner",
    "build_retention_checks",
    "summarize_retention_artifacts",
]
