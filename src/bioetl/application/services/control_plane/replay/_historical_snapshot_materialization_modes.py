"""Historical snapshot materialization mode constants."""

from __future__ import annotations

LIVE_CAPTURE_SNAPSHOT_MATERIALIZED = "live_capture_snapshot_materialized"
MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION = (
    "mixed_post_manifest_snapshot_materialization"
)

POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES = frozenset(
    {
        LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
        "historical_source_snapshot_certified",
        "historical_composite_replay_envelope_certified",
    }
)

__all__ = [
    "LIVE_CAPTURE_SNAPSHOT_MATERIALIZED",
    "MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION",
    "POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES",
]
