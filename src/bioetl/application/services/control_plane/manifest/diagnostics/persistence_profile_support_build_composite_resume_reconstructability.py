"""Extracted build_composite_resume_reconstructability for the hotspot coverage floor (#11016)."""

from __future__ import annotations

def build_composite_resume_reconstructability(
    *,
    composite_execution_context: bool,
    composite_resume_rich_replay_supported: bool,
) -> dict[str, object]:
    """Return the published checkpoint reconstruction scope for composite runs."""
    if composite_execution_context and composite_resume_rich_replay_supported:
        return {
            "scope": "rich_composite_resume",
            "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
            "reconstructs": [
                "state",
                "seed_completed",
                "seed_result",
                "dependency_results",
                "enrichment_results",
                "merge_result",
                "last_event_id",
                "last_event_occurred_at",
            ],
            "does_not_reconstruct": [],
            "forensic_grade_supported": True,
        }
    return {
        "scope": "coarse_grained_composite_resume",
        "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
        "reconstructs": [
            "state",
            "seed_completed",
            "merge_completed",
            "last_event_id",
            "last_event_occurred_at",
        ],
        "does_not_reconstruct": [
            "per_provider_result_maps",
            "rich_checkpoint_payloads",
        ],
        "forensic_grade_supported": False,
    }
