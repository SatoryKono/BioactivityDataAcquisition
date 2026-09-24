"""Extracted build_alert_signals for the hotspot coverage floor (#11016)."""

from __future__ import annotations


def build_alert_signals(
    *,
    latest_status: str | None,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
    composite_resume_reconstructability_gap: bool,
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
    required_persistence_profile_missing_requirements: list[str],
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> dict[str, bool]:
    """Map diagnostics summary to alert-oriented boolean signals."""
    latest_status_normalized = (latest_status or "").strip().lower()
    has_artifact_refs = len(artifact_refs) > 0
    immutable_input_snapshot_gap = (
        "immutable_input_snapshots" in replay_ready_missing_requirements
    )
    strict_replay_boundary_gap = (
        "strict_replay_execution_context_support" in replay_ready_missing_requirements
    )
    reproducible_semantic_output_mode_gap = (
        "reproducible_semantic_output_mode" in replay_ready_missing_requirements
    )
    produced_artifact_trace_gap = (
        "produced_artifact_trace" in replay_ready_missing_requirements
    )
    lineage_closure_boundary_gap = (
        "lineage_closure_boundary_support" in forensic_grade_missing_requirements
    )
    return {
        "run_failed": latest_status_normalized == "failed",
        "run_shutdown": latest_status_normalized == "shutdown",
        "artifact_linkage_gap": missing_link_count > 0,
        "lineage_gap": has_artifact_refs and not lineage_fragment_ids,
        "immutable_input_snapshot_gap": immutable_input_snapshot_gap,
        "strict_replay_boundary_gap": strict_replay_boundary_gap,
        "reproducible_semantic_output_mode_gap": (
            reproducible_semantic_output_mode_gap
        ),
        "produced_artifact_trace_gap": produced_artifact_trace_gap,
        "lineage_closure_boundary_gap": lineage_closure_boundary_gap,
        "composite_resume_reconstructability_gap": (
            composite_resume_reconstructability_gap
        ),
        "required_persistence_profile_gap": bool(
            required_persistence_profile_missing_requirements
        ),
        "replay_ready_gap": bool(replay_ready_missing_requirements),
        "forensic_grade_gap": bool(forensic_grade_missing_requirements),
        "dq_signal_present": dq_signal_present,
        "cross_validation_signal_present": cross_validation_signal_present,
    }
