"""Input-snapshot materialization summary helpers."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane.replay.historical_certification import (
    MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION,
)


def resolve_post_manifest_input_snapshot_materialization_mode(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Return the deterministic post-manifest materialization mode summary."""
    modes = sorted(
        {
            str(snapshot.get("materialization_mode") or "").strip()
            for snapshot in input_snapshots
            if isinstance(snapshot, Mapping)
            and str(snapshot.get("materialization_mode") or "").strip()
        }
    )
    if not modes:
        return None
    if len(modes) == 1:
        return modes[0]
    return MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION


__all__ = ["resolve_post_manifest_input_snapshot_materialization_mode"]
