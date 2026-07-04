"""Operator-facing replay mode labels for manifest diagnostics."""

from __future__ import annotations


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


__all__ = ["_resolve_operator_replay_mode"]
