"""Persistence and alert helpers for manifest diagnostics."""

from __future__ import annotations

from typing import cast

from bioetl.domain.control_plane.reproducibility_profiles import (
    build_lineage_closure_boundary as _build_lineage_closure_boundary,
)


def missing_replay_ready_requirements(
    *,
    strict_replay_execution_context_supported: bool,
    exact_replay_supported: bool,
    immutable_input_snapshots_present: bool,
    effective_config_artifact_present: bool,
) -> list[str]:
    """Return replay-ready persistence requirements missing for this run."""
    requirements = (
        (
            "strict_replay_execution_context_support",
            strict_replay_execution_context_supported,
        ),
        ("exact_replay_capability", exact_replay_supported),
        ("immutable_input_snapshots", immutable_input_snapshots_present),
        ("effective_config_artifact", effective_config_artifact_present),
    )
    return [name for name, present in requirements if not present]


def resolve_required_profile_requirements(
    *,
    required_profile: str,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> tuple[str, list[str]]:
    """Return canonical required profile and its unmet requirements."""
    if required_profile == "forensic_grade":
        return required_profile, list(forensic_grade_missing_requirements)
    if required_profile == "replay_ready":
        return required_profile, list(replay_ready_missing_requirements)
    return "degraded_observable", []


def claims_payload(
    *,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> dict[str, bool]:
    """Return profile claim booleans derived from unmet requirements."""
    return {
        "degraded_observable": True,
        "replay_ready": not replay_ready_missing_requirements,
        "forensic_grade": not forensic_grade_missing_requirements,
    }


def build_lineage_closure_boundary(
    *,
    provider: object,
    entity: object,
    contract_ref: object,
) -> dict[str, object]:
    """Return the published lineage-closure boundary for one manifested run."""
    execution_context = (
        "composite" if str(provider or "").strip() == "composite" else "source"
    )
    return _build_lineage_closure_boundary(
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
        execution_context=execution_context,
    )


def build_persistence_profile(
    *,
    base_summary: dict[str, object],
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
) -> dict[str, object]:
    """Classify the current run's persisted evidence against explicit profiles."""
    lineage_closure_boundary = cast(
        "dict[str, object]",
        base_summary.get("lineage_closure_boundary", {}),
    )
    lineage_closure_boundary_supported = bool(
        lineage_closure_boundary.get("supported", False)
    )
    replay_family_contract = cast(
        "dict[str, object]",
        base_summary.get("replay_family_contract", {}),
    )
    effective_config_artifact_present = bool(
        str(base_summary.get("effective_config_artifact_id") or "").strip()
    )
    immutable_input_snapshots_present = bool(base_summary.get("input_snapshot_ids", []))
    exact_replay_supported = bool(base_summary.get("exact_replay_eligible", False))
    exact_replay_boundary = str(
        base_summary.get("exact_replay_support_boundary")
        or "snapshot_backed_source_runs_only"
    )
    strict_replay_execution_context_supported = bool(
        replay_family_contract.get(
            "strict_exact_replay_supported",
            exact_replay_boundary == "snapshot_backed_source_runs_only",
        )
    )
    artifact_lineage_links_complete = not artifact_refs or (
        missing_link_count == 0 and bool(lineage_fragment_ids)
    )
    replay_ready_missing_requirements = missing_replay_ready_requirements(
        strict_replay_execution_context_supported=(
            strict_replay_execution_context_supported
        ),
        exact_replay_supported=exact_replay_supported,
        immutable_input_snapshots_present=immutable_input_snapshots_present,
        effective_config_artifact_present=effective_config_artifact_present,
    )
    forensic_grade_missing_requirements = list(replay_ready_missing_requirements)
    if not ledger_entries_present:
        forensic_grade_missing_requirements.append("run_ledger_history")
    if not artifact_lineage_links_complete:
        forensic_grade_missing_requirements.append("artifact_lineage_links")
    if not lineage_closure_boundary_supported:
        forensic_grade_missing_requirements.append("lineage_closure_boundary_support")
    required_profile = str(
        base_summary.get("required_persistence_profile") or "degraded_observable"
    )
    required_profile, required_profile_missing_requirements = (
        resolve_required_profile_requirements(
            required_profile=required_profile,
            replay_ready_missing_requirements=replay_ready_missing_requirements,
            forensic_grade_missing_requirements=forensic_grade_missing_requirements,
        )
    )
    attained_profile = "degraded_observable"
    if not replay_ready_missing_requirements:
        attained_profile = "replay_ready"
    if not forensic_grade_missing_requirements:
        attained_profile = "forensic_grade"
    return {
        "attained_profile": attained_profile,
        "required_profile": required_profile,
        "required_profile_satisfied": not required_profile_missing_requirements,
        "claims": claims_payload(
            replay_ready_missing_requirements=replay_ready_missing_requirements,
            forensic_grade_missing_requirements=forensic_grade_missing_requirements,
        ),
        "surfaces": {
            "control_plane_manifest": True,
            "effective_config_artifact": effective_config_artifact_present,
            "strict_replay_execution_context_support": (
                strict_replay_execution_context_supported
            ),
            "immutable_input_snapshots": immutable_input_snapshots_present,
            "exact_replay_capability": exact_replay_supported,
            "run_ledger_history": ledger_entries_present,
            "artifact_lineage_links": artifact_lineage_links_complete,
            "lineage_closure_boundary_support": lineage_closure_boundary_supported,
        },
        "required_profile_missing_requirements": required_profile_missing_requirements,
        "replay_ready_missing_requirements": replay_ready_missing_requirements,
        "forensic_grade_missing_requirements": forensic_grade_missing_requirements,
        "composite_resume_reconstructability": {
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
        },
        "lineage_closure_boundary": lineage_closure_boundary,
    }


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
    step_by_signal = (
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
            (
                "Persist immutable cached Bronze input snapshots before treating "
                "this run as strict exact-replay capable."
            ),
        ),
        (
            "strict_replay_boundary_gap",
            (
                "Treat this execution context as outside the strict exact-replay "
                "support boundary; use rebuild/resume semantics instead of exact replay."
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
            "required_persistence_profile_gap",
            (
                "Current persisted surfaces do not satisfy the declared required "
                "persistence profile for this run."
            ),
        ),
        (
            "composite_resume_reconstructability_gap",
            (
                "Treat composite resume as checkpoint snapshot plus ledger suffix "
                "replay only; do not expect per-provider result maps or other rich "
                "checkpoint payloads to be reconstructed."
            ),
        ),
        (
            "replay_ready_gap",
            (
                "Review replay-ready persistence requirements before treating this "
                "run as exact-replay capable."
            ),
        ),
        (
            "forensic_grade_gap",
            (
                "Review forensic-grade persistence requirements before using this "
                "run for full trace/debug reconstruction."
            ),
        ),
        (
            "dq_signal_present",
            (
                "Review DQ report artifacts, rule IDs, and contract policy anchors "
                "before retry or escalation."
            ),
        ),
        (
            "cross_validation_signal_present",
            (
                "Review cross-validation mismatch outcomes and composite policy "
                "anchors before retry or quarantine changes."
            ),
        ),
        (
            "run_shutdown",
            "Confirm graceful shutdown reason and resume policy compatibility.",
        ),
    )
    steps = [
        message
        for signal, message in step_by_signal
        if alert_signals.get(signal, False)
    ]
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps
