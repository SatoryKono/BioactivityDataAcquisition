"""Immutable snapshot certification and materialization mode contracts."""

from __future__ import annotations

from collections.abc import Mapping

HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED = "historical_source_snapshot_certified"
HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED = (
    "historical_composite_replay_envelope_certified"
)
LIVE_CAPTURE_SNAPSHOT_MATERIALIZED = "live_capture_snapshot_materialized"
MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION = (
    "mixed_post_manifest_snapshot_materialization"
)

POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES = frozenset(
    {
        LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
        HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
        HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    }
)


def _snapshot_materialization_mode(snapshot: Mapping[str, object]) -> str:
    """Return the stripped materialization mode or empty string."""
    return str(snapshot.get("materialization_mode") or "").strip()


def _collect_materialization_modes(
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Collect distinct non-empty materialization modes in sorted order."""
    collected: list[str] = []
    for snapshot in input_snapshots:
        raw_snapshot: object = snapshot
        if not isinstance(raw_snapshot, Mapping):
            continue
        mode = _snapshot_materialization_mode(raw_snapshot)
        if mode:
            collected.append(mode)
    return sorted(set(collected))


def resolve_post_manifest_input_snapshot_materialization_mode(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Return the deterministic post-manifest materialization mode summary."""
    modes = _collect_materialization_modes(input_snapshots)
    if not modes:
        return None
    if len(modes) == 1:
        return modes[0]
    return MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION


__all__ = [
    "HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED",
    "HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED",
    "LIVE_CAPTURE_SNAPSHOT_MATERIALIZED",
    "MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION",
    "POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES",
    "resolve_post_manifest_input_snapshot_materialization_mode",
]
