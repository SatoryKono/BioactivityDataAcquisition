"""Replay, resume, and input-snapshot helpers for manifest diagnostics."""

from __future__ import annotations

__all__ = [
    "_assess_manifest_reproducibility_policy",
    "_build_replay_parentage",
    "_build_resume_contract",
    "_resolve_exact_replay_support_boundary",
    "_resolve_replay_family_contract",
]

from bioetl.application.services.control_plane._run_manifest_diagnostics_replay_helpers import (
    _build_replay_parentage,
    _is_composite_execution_context,
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_family_contract,
    _resolve_reproducibility_profile,
    _resolve_requested_checkpoint_compatibility_policy,
    _resolve_required_persistence_profile,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay_state import (
    _resolve_continuation_mode,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    ReplayReadinessVerdict,
    ReproducibilityPolicyAssessment,
    assess_reproducibility_policy,
    resolve_replay_readiness_verdict,
)


def _assess_manifest_reproducibility_policy(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    replay_family_contract: dict[str, object],
) -> ReproducibilityPolicyAssessment:
    """Return the central reproducibility policy verdict for one manifest."""
    return assess_reproducibility_policy(
        source_refs=manifest.source_refs,
        required_persistence_profile=_resolve_required_persistence_profile(manifest),
        strict_exact_replay_supported=bool(
            replay_family_contract.get("strict_exact_replay_supported", False)
        ),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=(
            replay_family_contract.get("contract")
            == "composite_snapshot_backed_exact_replay"
        ),
        replay_capability=manifest.replay_capability,
        run_type=manifest.run_type,
    )


def _resolve_manifest_replay_readiness_verdict(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
    continuation_mode: str,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> ReplayReadinessVerdict:
    """Return the runtime diagnostics verdict without conflating run modes."""
    lifecycle_projection_only = (
        _is_composite_execution_context(manifest)
        and "ledger_suffix" in continuation_mode
        and manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    )
    profile = _resolve_reproducibility_profile(manifest)
    runtime_blocking_gaps = list(policy_assessment.blocking_gaps)
    if (
        profile.strict_exact_replay_supported
        and (
            policy_assessment.strict_requirement_requested
            or manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        )
        and not manifest.code_provenance.dependency_lock_hash
    ):
        runtime_blocking_gaps.append("dependency_lock_provenance")
    return resolve_replay_readiness_verdict(
        replay_capability=manifest.replay_capability,
        strict_requirement_requested=policy_assessment.strict_requirement_requested,
        strict_exact_replay_supported=profile.strict_exact_replay_supported,
        blocking_gaps=tuple(dict.fromkeys(runtime_blocking_gaps)),
        exact_replay_requested=requested_exact_replay,
        resume_requested=resume_requested,
        run_type=manifest.run_type,
        debug_only=not profile.strict_exact_replay_supported,
        lifecycle_projection_only=lifecycle_projection_only,
    )


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
        "semantic_identity_anchor": "execution_fingerprint",
        "occurrence_identity_anchor": "run_id",
    }
