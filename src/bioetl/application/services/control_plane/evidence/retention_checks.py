"""Bounded check builders for control-plane retention evidence."""

from __future__ import annotations

from bioetl.application.services.control_plane.evidence.models import EvidenceCheck
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunManifest,
)


def retention_evidence_checks(
    manifest: RunManifest,
    artifacts: tuple[ControlPlaneArtifactRef, ...],
) -> tuple[EvidenceCheck, ...]:
    """Build explicit retention, evidence-floor, and archive results."""
    required_profile = _required_profile(manifest)
    strict_profile = required_profile in {"replay_ready", "forensic_grade"}
    delete_count = sum(
        artifact.decision is ControlPlaneArtifactLifecycleDecision.DELETE
        for artifact in artifacts
    )
    return (
        _retention_policy_check(delete_count),
        _evidence_floor_check(
            required_profile,
            strict_profile=strict_profile,
            protected=_evidence_floor_protected(artifacts),
        ),
        _required_evidence_check(
            _missing_surfaces(artifacts, strict_profile=strict_profile)
        ),
        EvidenceCheck(
            "archive",
            "UNKNOWN",
            "archive_evidence_not_recorded",
            "The local lifecycle plan does not attest external archive availability.",
        ),
    )


def _required_profile(manifest: RunManifest) -> str:
    return str(
        manifest.launch_context.get("required_persistence_profile")
        or "degraded_observable"
    ).strip()


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
    strict_profile: bool,
) -> list[str]:
    required = {
        ControlPlaneArtifactSurface.RUN_MANIFEST,
        ControlPlaneArtifactSurface.RUN_LEDGER,
    }
    if strict_profile:
        required.update(
            {
                ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
                ControlPlaneArtifactSurface.LINEAGE,
            }
        )
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
    strict_profile: bool,
    protected: bool,
) -> EvidenceCheck:
    if not strict_profile:
        return EvidenceCheck(
            "evidence_floor",
            "OK",
            "reproducibility_evidence_floor_satisfied",
            "No strict replay evidence floor is declared for this run.",
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


def _required_evidence_check(missing_surfaces: list[str]) -> EvidenceCheck:
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


__all__ = ["retention_evidence_checks"]
