"""Exact-replay blocker helpers for run-manifest diagnostics."""

from __future__ import annotations

from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)

__all__ = [
    "append_mode_exact_replay_blockers",
    "dependency_lock_exact_replay_blockers",
    "profile_exact_replay_blockers",
    "requires_dependency_lock_provenance",
    "snapshot_exact_replay_blockers",
]


def profile_exact_replay_blockers(profile: object) -> list[str]:
    if getattr(profile, "strict_exact_replay_supported", False):
        return []
    return ["family_outside_supported_exact_replay_boundary"]


def append_mode_exact_replay_blockers(append_mode_sinks: list[str]) -> list[str]:
    if not append_mode_sinks:
        return []
    return ["append_mode_semantic_outputs"]


def snapshot_exact_replay_blockers(
    *,
    manifest: RunManifest,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    snapshot_envelope = policy_assessment.snapshot_envelope
    if not getattr(snapshot_envelope, "any_input_snapshots", False):
        return ["immutable_input_snapshots_missing"]
    if not getattr(snapshot_envelope, "full_snapshot_envelope", False):
        return [
            "partial_input_snapshot_envelope",
            *(
                f"input_snapshot_missing:{source_ref}"
                for source_ref in getattr(
                    snapshot_envelope, "missing_snapshot_source_refs", []
                )
            ),
        ]
    if manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return ["exact_replay_capability_unavailable"]
    return []


def dependency_lock_exact_replay_blockers(
    *,
    manifest: RunManifest,
    profile: object,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    if not requires_dependency_lock_provenance(
        manifest=manifest,
        profile=profile,
        policy_assessment=policy_assessment,
    ):
        return []
    return ["dependency_lock_provenance_missing"]


def requires_dependency_lock_provenance(
    *,
    manifest: RunManifest,
    profile: object,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> bool:
    if not getattr(profile, "strict_exact_replay_supported", False):
        return False
    if (
        not getattr(policy_assessment, "strict_requirement_requested", False)
        and manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        return False
    return not manifest.code_provenance.dependency_lock_hash
