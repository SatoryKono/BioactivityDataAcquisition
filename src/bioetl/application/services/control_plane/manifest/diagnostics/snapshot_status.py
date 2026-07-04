"""Input-snapshot status labels for manifest diagnostics."""

from __future__ import annotations


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


__all__ = ["_resolve_snapshot_status"]
