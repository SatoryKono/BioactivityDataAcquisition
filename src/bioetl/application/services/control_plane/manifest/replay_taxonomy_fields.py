"""Field definitions for replay-taxonomy projection payloads."""

from __future__ import annotations

REPLAY_TAXONOMY_FIELDS: tuple[str, ...] = (
    "replay_capability",
    "requested_exact_replay",
    "exact_replay_support_boundary",
    "replay_family_contract",
    "replay_support_state",
    "post_capture_replayable_parent_supported",
    "post_capture_replayable_parent_boundary",
    "historical_live_run_upgrade_policy",
    "historical_live_run_upgrade_boundary",
    "historical_live_run_upgrade_reason",
    "broader_historical_exact_replay_policy",
    "broader_historical_exact_replay_boundary",
    "broader_historical_exact_replay_reason",
    "broader_historical_exact_replay_state",
    "historical_live_run_upgrade_state",
    "replay_occurrence_kind",
    "source_posture",
    "input_snapshot_missing_source_refs",
    "replay_capability_reason",
    "replay_mode",
    "continuation_mode",
    "operator_replay_mode",
    "replay_resume_rebuild_verdict",
    "replay_next_action",
    "exact_replay_eligible",
    "exact_replay_blockers",
    "replay_readiness_verdict",
    "append_mode_semantic_sinks",
    "resume_contract",
    "resume_diagnostics",
    "lineage_closure_boundary",
)

LIST_DEFAULTS: dict[str, object] = {
    "input_snapshot_missing_source_refs": [],
    "exact_replay_blockers": [],
    "append_mode_semantic_sinks": [],
}
