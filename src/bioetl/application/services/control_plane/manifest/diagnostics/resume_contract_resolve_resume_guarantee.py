"""Extracted _resolve_resume_guarantee for the hotspot coverage floor (#11016)."""

from __future__ import annotations


def _resolve_resume_guarantee(
    *,
    continuation_mode: str,
) -> tuple[str, str, bool]:
    """Map continuation taxonomy to the published resume guarantee."""
    if continuation_mode == "exact_replay":
        return (
            "strict_evidence_boundary_exact_replay",
            "manifest_input_snapshots_and_control_plane_anchors",
            False,
        )
    if continuation_mode == "checkpoint_snapshot_plus_ledger_suffix_resume":
        return (
            "bounded_composite_reconstructive_resume",
            "checkpoint_snapshot_plus_ledger_suffix",
            True,
        )
    if continuation_mode == "checkpoint_snapshot_only_resume":
        return (
            "compatibility_checked_checkpoint_snapshot_resume",
            "checkpoint_snapshot",
            False,
        )
    if continuation_mode == "full_scan_idempotent_rebuild":
        return (
            "idempotent_rebuild_not_checkpoint_resume",
            "full_scan_content_hash_deduplication",
            False,
        )
    return ("no_resume_guarantee", "none", False)
