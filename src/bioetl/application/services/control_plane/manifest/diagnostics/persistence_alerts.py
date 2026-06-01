"""Alert- and next-step helpers for manifest diagnostics persistence output."""

from __future__ import annotations

__all__ = ["build_alert_signals", "build_next_steps"]

_NEXT_STEP_BY_SIGNAL: tuple[tuple[str, str], ...] = (
    (
        "run_failed",
        "Inspect failure classification and decide retry/quarantine/escalation.",
    ),
    (
        "artifact_linkage_gap",
        "Validate artifact publication metadata and repair dataset/lineage links.",
    ),
    (
        "lineage_gap",
        "Investigate lineage persistence for published artifacts before restart.",
    ),
    (
        "immutable_input_snapshot_gap",
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
    ),
    (
        "strict_replay_boundary_gap",
        (
            "Treat this execution context as outside the strict exact-replay "
            "support boundary; use rebuild/resume semantics instead of exact replay."
        ),
    ),
    (
        "reproducible_semantic_output_mode_gap",
        (
            "Replace append-mode Silver/Gold semantic sinks before claiming "
            "replay-ready or forensic-grade reproducibility."
        ),
    ),
    (
        "lineage_closure_boundary_gap",
        (
            "Treat this pipeline family as outside the current operator-grade "
            "lineage closure boundary; do not claim forensic-grade trace/debug "
            "support for it."
        ),
    ),
    (
        "produced_artifact_trace_gap",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
    ),
    (
        "required_persistence_profile_gap",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
    ),
    (
        "composite_resume_reconstructability_gap",
        (
            "Treat composite resume as checkpoint snapshot plus ledger suffix "
            "replay only when rich checkpoint payload evidence is missing; "
            "otherwise validate the recorded seed/dependency/enrichment/merge "
            "payloads before forensic replay claims."
        ),
    ),
    (
        "replay_ready_gap",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
    ),
    (
        "forensic_grade_gap",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ),
    (
        "dq_signal_present",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ),
    (
        "cross_validation_signal_present",
        "Review cross-validation mismatch outcomes and composite policy anchors before retry or quarantine changes.",
    ),
    (
        "run_shutdown",
        "Confirm graceful shutdown reason and resume policy compatibility.",
    ),
)


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


def build_next_steps(alert_signals: dict[str, bool]) -> list[str]:
    """Return operator-oriented next steps based on active alert signals."""
    steps = [
        message
        for signal, message in _NEXT_STEP_BY_SIGNAL
        if alert_signals.get(signal, False)
    ]
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps
