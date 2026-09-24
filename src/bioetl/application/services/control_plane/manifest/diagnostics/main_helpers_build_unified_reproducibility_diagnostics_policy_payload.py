"""Extracted _build_unified_reproducibility_diagnostics_policy_payload for the hotspot coverage floor (#11016)."""

from __future__ import annotations


def _build_unified_reproducibility_diagnostics_policy_payload(
    summary: dict[str, object],
    persistence_profile: dict[str, object],
) -> dict[str, object]:
    """Build policy section of unified reproducibility diagnostics."""
    return {
        "required_persistence_profile": summary.get("required_persistence_profile"),
        "attained_profile": persistence_profile.get("attained_profile"),
        "required_profile_satisfied": persistence_profile.get(
            "required_profile_satisfied"
        ),
        "required_profile_missing_requirements": persistence_profile.get(
            "required_profile_missing_requirements",
            [],
        ),
        "replay_capability": summary.get("replay_capability"),
        "replay_control_plane_state": summary.get("replay_control_plane_state"),
        "replay_readiness_verdict": summary.get("replay_readiness_verdict"),
        "operator_replay_mode": summary.get("operator_replay_mode"),
        "replay_mode": summary.get("replay_mode"),
        "continuation_mode": summary.get("continuation_mode"),
        "replay_family_contract": summary.get("replay_family_contract"),
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
        "post_capture_replayable_parent_supported": summary.get(
            "post_capture_replayable_parent_supported"
        ),
        "post_capture_replayable_parent_boundary": summary.get(
            "post_capture_replayable_parent_boundary"
        ),
        "historical_live_run_upgrade_policy": summary.get(
            "historical_live_run_upgrade_policy"
        ),
        "historical_live_run_upgrade_boundary": summary.get(
            "historical_live_run_upgrade_boundary"
        ),
        "historical_live_run_upgrade_reason": summary.get(
            "historical_live_run_upgrade_reason"
        ),
        "broader_historical_exact_replay_policy": summary.get(
            "broader_historical_exact_replay_policy"
        ),
        "broader_historical_exact_replay_boundary": summary.get(
            "broader_historical_exact_replay_boundary"
        ),
        "broader_historical_exact_replay_reason": summary.get(
            "broader_historical_exact_replay_reason"
        ),
        "broader_historical_exact_replay_state": summary.get(
            "broader_historical_exact_replay_state"
        ),
        "historical_live_run_upgrade_state": summary.get(
            "historical_live_run_upgrade_state"
        ),
        "replay_occurrence_kind": summary.get("replay_occurrence_kind"),
        "exact_replay_blockers": summary.get("exact_replay_blockers", []),
        "capability_assessment": summary.get(
            "replay_capability_assessment",
            {},
        ),
    }
