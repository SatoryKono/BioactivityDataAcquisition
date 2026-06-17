"""Checkpoint/resume contract helpers for manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_policy import (
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_reproducibility_profile,
    _resolve_requested_checkpoint_compatibility_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_state import (
    _resolve_continuation_mode,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    ReproducibilityPolicyAssessment,
)


def _resolve_resume_guarantee(
    *,
    continuation_mode: str,
) -> tuple[str, str, bool]:
    """Map continuation taxonomy to the published resume guarantee."""
    if continuation_mode == "exact_replay":
        return (
            "strict_evidence_boundary_exact_replay",
            "manifest_input_snapshots_and_control_plane_anchors",
            False,
        )
    if continuation_mode == "checkpoint_snapshot_plus_ledger_suffix_resume":
        return (
            "bounded_composite_reconstructive_resume",
            "checkpoint_snapshot_plus_ledger_suffix",
            True,
        )
    if continuation_mode == "checkpoint_snapshot_only_resume":
        return (
            "compatibility_checked_checkpoint_snapshot_resume",
            "checkpoint_snapshot",
            False,
        )
    if continuation_mode == "full_scan_idempotent_rebuild":
        return (
            "idempotent_rebuild_not_checkpoint_resume",
            "full_scan_content_hash_deduplication",
            False,
        )
    return ("no_resume_guarantee", "none", False)


def _build_resume_contract(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> dict[str, object]:
    """Return the published checkpoint/resume contract for one manifested run."""
    profile = _resolve_reproducibility_profile(manifest)
    requested_policy = _resolve_requested_checkpoint_compatibility_policy(manifest)
    required_persistence_profile = policy_assessment.required_persistence_profile
    applied_policy = _resolve_applied_checkpoint_compatibility_policy(
        requested_exact_replay=requested_exact_replay,
        requested_policy=requested_policy,
        required_persistence_profile=required_persistence_profile,
    )
    strict_replay_requested = (
        requested_exact_replay
        or required_persistence_profile in STRICT_PERSISTENCE_PROFILES
    )
    is_composite = _is_composite_execution_context(manifest)
    execution_context = "composite" if is_composite else "ordinary"
    continuation_mode = _resolve_continuation_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    guarantee, evidence_source, ledger_suffix_replay = _resolve_resume_guarantee(
        continuation_mode=continuation_mode,
    )
    return {
        "resume_requested": resume_requested,
        "requested_exact_replay": requested_exact_replay,
        "requested_checkpoint_compatibility_policy": requested_policy,
        "applied_checkpoint_compatibility_policy": applied_policy,
        "strict_replay_safe": (
            strict_replay_requested
            and applied_policy == "hard_fail"
            and profile.strict_exact_replay_supported
            and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
            and bool(manifest.code_provenance.dependency_lock_hash)
        ),
        "execution_context": execution_context,
        "resume_mode": (
            "checkpoint_snapshot_plus_ledger_suffix"
            if is_composite
            else "checkpoint_snapshot_only"
        ),
        "continuation_mode": continuation_mode,
        "resume_guarantee": guarantee,
        "resume_evidence_source": evidence_source,
        "ledger_suffix_replay": ledger_suffix_replay,
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": "run_id",
    }


__all__ = ["_build_resume_contract"]
