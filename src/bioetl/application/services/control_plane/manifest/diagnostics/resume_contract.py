"""Checkpoint/resume contract helpers for manifest diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.checkpoint_policy import (
    _resolve_requested_checkpoint_compatibility_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.checkpoint_policy import (
    resolve_applied_checkpoint_compatibility_policy as _resolve_applied_checkpoint_compatibility_policy,
)
from bioetl.application.services.control_plane.manifest.diagnostics.resume_contract_resolve_resume_guarantee import (
    _resolve_resume_guarantee,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    ReproducibilityPolicyAssessment,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family_context import (
        ReplayFamilyContext,
    )


def _build_resume_contract(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    continuation_mode: str,
    policy_assessment: ReproducibilityPolicyAssessment,
    replay_family_context: ReplayFamilyContext,
) -> dict[str, object]:
    """Return the published checkpoint/resume contract for one manifested run."""
    profile = replay_family_context.profile
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
