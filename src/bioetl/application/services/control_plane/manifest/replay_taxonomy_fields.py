"""Field definitions for replay-taxonomy projection payloads."""

from __future__ import annotations

from bioetl.application.ports.control_plane import (
    REPLAY_TAXONOMY_FIELDS as REPLAY_TAXONOMY_FIELDS,
)

LIST_DEFAULTS: dict[str, tuple[object, ...]] = {
    "input_snapshot_missing_source_refs": (),
    "exact_replay_blockers": (),
    "append_mode_semantic_sinks": (),
}
