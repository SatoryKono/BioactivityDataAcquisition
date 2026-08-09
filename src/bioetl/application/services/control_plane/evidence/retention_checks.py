"""Bounded check builders for control-plane retention evidence."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services.control_plane.evidence.persistence_profile import (
    STRICT_PERSISTENCE_PROFILES,
    resolve_persistence_profile,
)
from bioetl.application.services.control_plane_evidence import EvidenceCheck
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunManifest,
)


def retention_evidence_checks(
    manifest: RunManifest,
    artifacts: tuple[ControlPlaneArtifactRef, ...],
    *,
    cutoff: datetime,
) -> tuple[EvidenceCheck, ...]:
    """Build explicit retention, evidence-floor, and archive results."""
    required_profile, profile_valid = resolve_persistence_profile(manifest)
    delete_count = sum(
        artifact.decision is ControlPlaneArtifactLifecycleDecision.DELETE
        for artifact in artifacts
    )
    return (
        _retention_policy_check(delete_count),
        _evidence_floor_check(
            required_profile,
            protected=_evidence_floor_protected(artifacts),
            profile_valid=profile_valid,
            stale=manifest.created_at < cutoff,
        ),
        _required_evidence_check(
            artifacts,
            required_profile=required_profile,
            profile_valid=profile_valid,
        ),
        _snapshot_evidence_check(
            manifest,
            artifacts,
            required_profile=required_profile,
            profile_valid=profile_valid,
        ),
        EvidenceCheck(
            "archive",
            "UNKNOWN",
            "archive_evidence_not_recorded",
            "The local lifecycle plan does not attest external archive availability.",
        ),
    )


def _evidence_floor_protected(
    artifacts: tuple[ControlPlaneArtifactRef, ...],
) -> bool:
    return any(
        reason.startswith("evidence_floor:")
        for artifact in artifacts
        for reason in artifact.protected_by
    )


def _missing_surfaces(
    artifacts: tuple[ControlPlaneArtifactRef, ...],
    *,
    required_profile: str,
    profile_valid: bool,
) -> list[str]:
    required = {ControlPlaneArtifactSurface.RUN_MANIFEST}
    if not profile_valid or required_profile == "forensic_grade":
        required.update(
            {
                ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
                ControlPlaneArtifactSurface.RUN_LEDGER,
                ControlPlaneArtifactSurface.LINEAGE,
            }
        )
    elif required_profile == "replay_ready":
        required.add(ControlPlaneArtifactSurface.EFFECTIVE_CONFIG)
    present = {artifact.surface for artifact in artifacts}
    return sorted(surface.value for surface in required - present)


def _retention_policy_check(delete_count: int) -> EvidenceCheck:
    if delete_count:
        return EvidenceCheck(
            "retention_policy",
            "ERROR",
            "retention_delete_candidates_present",
            f"{delete_count} selected-run artifacts are delete candidates.",
        )
    return EvidenceCheck(
        "retention_policy",
        "OK",
        "retention_policy_satisfied",
        "Selected-run artifacts are retained by the current dry-run policy.",
    )


def _evidence_floor_check(
    required_profile: str,
    *,
    protected: bool,
    profile_valid: bool,
    stale: bool,
) -> EvidenceCheck:
    if not profile_valid:
        return EvidenceCheck(
            "evidence_floor",
            "ERROR",
            "retention_persistence_profile_unsupported",
            "Retention validation rejects an unsupported persistence profile.",
        )
    if required_profile not in STRICT_PERSISTENCE_PROFILES:
        return EvidenceCheck(
            "evidence_floor",
            "OK",
            "reproducibility_evidence_floor_satisfied",
            "No strict replay evidence floor is declared for this run.",
        )
    if not stale:
        return EvidenceCheck(
            "evidence_floor",
            "OK",
            "reproducibility_evidence_within_retention",
            "Strict replay evidence remains inside the retention window.",
        )
    if protected:
        return EvidenceCheck(
            "evidence_floor",
            "OK",
            "reproducibility_evidence_floor_satisfied",
            f"The {required_profile} evidence floor is protected.",
        )
    return EvidenceCheck(
        "evidence_floor",
        "ERROR",
        "reproducibility_evidence_floor_unprotected",
        f"The {required_profile} evidence floor lacks planner protection.",
    )


def _required_evidence_check(
    artifacts: tuple[ControlPlaneArtifactRef, ...],
    *,
    required_profile: str,
    profile_valid: bool,
) -> EvidenceCheck:
    missing_surfaces = _missing_surfaces(
        artifacts,
        required_profile=required_profile,
        profile_valid=profile_valid,
    )
    if missing_surfaces:
        return EvidenceCheck(
            "required_evidence",
            "ERROR",
            "required_evidence_surfaces_missing",
            "Missing lifecycle evidence surfaces: " + ", ".join(missing_surfaces),
        )
    return EvidenceCheck(
        "required_evidence",
        "OK",
        "required_evidence_surfaces_present",
        "Required lifecycle evidence surfaces are represented in the plan.",
    )


def _snapshot_evidence_check(
    manifest: RunManifest,
    artifacts: tuple[ControlPlaneArtifactRef, ...],
    *,
    required_profile: str,
    profile_valid: bool,
) -> EvidenceCheck:
    if not profile_valid:
        return EvidenceCheck(
            "snapshot_evidence",
            "ERROR",
            "retention_persistence_profile_unsupported",
            "Snapshot requirements cannot be evaluated for an unsupported profile.",
        )
    if required_profile not in STRICT_PERSISTENCE_PROFILES:
        return EvidenceCheck(
            "snapshot_evidence",
            "OK",
            "snapshot_evidence_not_required",
            "The degraded observable profile does not require snapshot evidence.",
        )
    snapshot_ids = {
        snapshot.snapshot_id
        for source in manifest.source_refs
        for snapshot in source.input_snapshots
    }
    if not snapshot_ids:
        return EvidenceCheck(
            "snapshot_evidence",
            "ERROR",
            "manifest_snapshot_evidence_missing",
            "The strict persistence profile requires manifest input snapshots.",
        )
    observed = any(
        artifact.surface is ControlPlaneArtifactSurface.CACHED_BRONZE
        and artifact.artifact_id in snapshot_ids
        for artifact in artifacts
    )
    if observed:
        return EvidenceCheck(
            "snapshot_evidence",
            "OK",
            "snapshot_lifecycle_evidence_present",
            "The lifecycle plan contains the manifested cached snapshot evidence.",
        )
    return EvidenceCheck(
        "snapshot_evidence",
        "UNKNOWN",
        "snapshot_lifecycle_evidence_not_observed",
        "The lifecycle plan cannot prove the manifested cached snapshot evidence.",
    )


__all__ = ["retention_evidence_checks"]
