"""Exact-replay blocker helpers for run-manifest diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane._run_manifest_diagnostics_replay_helpers import (
    _append_mode_exact_replay_blockers,
    _collect_append_mode_semantic_sinks,
    _dependency_lock_exact_replay_blockers,
    _profile_exact_replay_blockers,
    _resolve_reproducibility_profile,
    _snapshot_exact_replay_blockers,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


def _resolve_exact_replay_blockers(
    *,
    manifest: RunManifest,
    policy_assessment: ReproducibilityPolicyAssessment,
) -> list[str]:
    """Return explicit blockers preventing exact replay eligibility."""
    profile = _resolve_reproducibility_profile(manifest)
    append_mode_sinks = _collect_append_mode_semantic_sinks(manifest)
    return [
        *_profile_exact_replay_blockers(profile),
        *_append_mode_exact_replay_blockers(append_mode_sinks),
        *_snapshot_exact_replay_blockers(
            manifest=manifest,
            policy_assessment=policy_assessment,
        ),
        *_dependency_lock_exact_replay_blockers(
            manifest=manifest,
            profile=profile,
            policy_assessment=policy_assessment,
        ),
    ]


__all__ = ["_resolve_exact_replay_blockers"]
