"""Replay label helpers for base manifest diagnostics summaries."""

from __future__ import annotations

from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


def _resolve_snapshot_status(
    *,
    input_snapshots: list[dict[str, object]],
    exact_replay_eligible: bool,
    replay_mode: str,
) -> str:
    """Return operator-facing completeness of immutable input snapshots."""
    if not input_snapshots:
        return "none"
    if exact_replay_eligible or replay_mode in {
        "exact_replay",
        "same_data_state_recovery",
    }:
        return "full"
    return "partial"


def _resolve_source_posture(
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return whether manifested sources are snapshot-backed or live/unknown."""
    snapshot_envelope = policy_assessment.snapshot_envelope
    if snapshot_envelope.full_snapshot_envelope:
        return "immutable_snapshot_envelope"
    if snapshot_envelope.any_input_snapshots:
        return "partial_snapshot_envelope"
    return "live_or_unknown_inputs"


def _resolve_operator_replay_mode(
    *,
    replay_mode: str,
    continuation_mode: str,
    replay_readiness_verdict: str,
) -> str:
    """Return a compact CLI label for exact replay/resume/rebuild triage."""
    if replay_readiness_verdict == "exact_replay_blocked":
        return "Exact Replay Blocked"
    if replay_readiness_verdict == "lifecycle_projection_only":
        return "Lifecycle Projection"
    if replay_readiness_verdict == "incremental_new_run":
        return "Incremental New Run"
    if replay_readiness_verdict == "debug_only":
        return "Debug Only"
    if replay_mode == "exact_replay":
        return "Exact Replay"
    if replay_mode == "resume" or "resume" in continuation_mode:
        return "Resume"
    return "Rebuild"


__all__ = [
    "_resolve_operator_replay_mode",
    "_resolve_snapshot_status",
    "_resolve_source_posture",
]
