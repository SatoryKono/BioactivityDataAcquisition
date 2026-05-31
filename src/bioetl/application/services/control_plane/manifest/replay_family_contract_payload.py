"""Replay-family contract payload assembly owned by the manifest seam."""

from __future__ import annotations


def build_replay_family_contract_payload(
    replay_family_contract: dict[str, object],
) -> dict[str, object]:
    """Return the bounded replay-family contract projection payload."""
    return {
        "replay_support_state": replay_family_contract.get("support_state"),
        "post_capture_replayable_parent_supported": replay_family_contract.get(
            "post_capture_replayable_parent_supported"
        ),
        "post_capture_replayable_parent_boundary": replay_family_contract.get(
            "post_capture_replayable_parent_boundary"
        ),
        "historical_live_run_upgrade_policy": replay_family_contract.get(
            "historical_live_run_upgrade_policy"
        ),
        "historical_live_run_upgrade_boundary": replay_family_contract.get(
            "historical_live_run_upgrade_boundary"
        ),
        "historical_live_run_upgrade_reason": replay_family_contract.get(
            "historical_live_run_upgrade_reason"
        ),
        "broader_historical_exact_replay_policy": replay_family_contract.get(
            "broader_historical_exact_replay_policy"
        ),
        "broader_historical_exact_replay_boundary": replay_family_contract.get(
            "broader_historical_exact_replay_boundary"
        ),
        "broader_historical_exact_replay_reason": replay_family_contract.get(
            "broader_historical_exact_replay_reason"
        ),
    }
