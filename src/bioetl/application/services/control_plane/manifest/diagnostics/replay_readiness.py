"""Replay-readiness verdict helpers for manifest diagnostics."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    ReplayReadinessVerdict,
    ReproducibilityPolicyAssessment,
    resolve_replay_readiness_verdict,
)
from bioetl.domain.control_plane.reproducibility_profiles import (
    ReproducibilityFamilyProfile,
    resolve_reproducibility_family_profile,
)


def _resolve_readiness_reproducibility_profile(
    manifest: RunManifest,
) -> ReproducibilityFamilyProfile:
    execution_context: Literal["source", "composite"] = (
        "composite" if _is_composite_execution_context(manifest) else "source"
    )
    return resolve_reproducibility_family_profile(
        provider=manifest.provider,
        entity=manifest.entity,
        contract_ref=manifest.code_provenance.contract_ref,
        execution_context=execution_context,
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
    profile = _resolve_readiness_reproducibility_profile(manifest)
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


__all__ = ["_resolve_manifest_replay_readiness_verdict"]
