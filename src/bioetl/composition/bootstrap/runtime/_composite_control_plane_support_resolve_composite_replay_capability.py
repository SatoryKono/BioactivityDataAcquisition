"""Extracted resolve_composite_replay_capability for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from bioetl.domain.control_plane import ReplayCapability, RunSourceRef

from bioetl.domain.control_plane.reproducibility_policy import (
    assess_reproducibility_policy,
)


def resolve_composite_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    required_persistence_profile: str,
    resume_requested: bool,
) -> ReplayCapability:
    """Return rebuild/resume capability for composite runs, never strict replay."""
    replay_capability = (
        ReplayCapability.RESUME_ONLY
        if resume_requested
        else ReplayCapability.REBUILD_ONLY
    )
    assessment = assess_reproducibility_policy(
        source_refs=source_refs,
        required_persistence_profile=required_persistence_profile,
        strict_exact_replay_supported=False,
        require_full_snapshot_envelope=True,
        replay_capability=replay_capability,
        resume_requested=resume_requested,
    )
    if (
        not assessment.required_profile_satisfied
        and "strict_replay_execution_context_support" in assessment.blocking_gaps
    ):
        raise RuntimeError(
            "Composite execution cannot satisfy required persistence profile "
            f"'{required_persistence_profile}' because composite execution is "
            "outside the strict exact-replay support boundary; use source-run "
            "exact replay or composite rebuild/resume semantics instead"
        )
    return replay_capability
