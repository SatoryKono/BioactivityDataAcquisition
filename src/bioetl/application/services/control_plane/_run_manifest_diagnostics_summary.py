"""Summary assembly helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _resolve_policy_value,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _is_composite_execution_context,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)


def _build_final_summary(
    manifest: RunManifest,
    base_summary: dict[str, object],
    ledger_entries: tuple[RunLedgerEntry, ...],
    family_counter: Counter[str],
    type_counter: Counter[str],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    dq_rule_ids: set[str],
    dq_dispositions: set[str],
    dq_report_paths: set[str],
    dq_violation_kinds: set[str],
    cross_validation_rule_ids: set[str],
    cross_validation_config_paths: set[str],
    cross_validation_quarantine_policies: set[str],
    cross_validation_replay_contracts: set[str],
    occurrence_only_diagnostic_scopes: set[str],
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
    missing_link_count: int,
    correlation_anchor_gaps: dict[str, int],
    resume_diagnostics: dict[str, object] | None,
) -> dict[str, object]:
    """Build final summary with all processed data."""
    latest_entry = ledger_entries[-1]
    planned_artifacts = cast(
        list[dict[str, object]],
        base_summary.get("planned_artifacts", []),
    )
    canonical_execution_identity_payload = build_execution_identity_payload(
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=cast("str | None", base_summary.get("pipeline_version")),
        effective_config_hash=cast(
            "str | None", base_summary.get("effective_config_hash")
        ),
        dq_contract_compatibility_hash=cast(
            "str | None", base_summary.get("dq_contract_compatibility_hash")
        ),
        contract_ref=cast("str | None", base_summary.get("contract_ref")),
        contract_version=cast("str | None", base_summary.get("contract_version")),
        effective_config_artifact_id=cast(
            "str | None", base_summary.get("effective_config_artifact_id")
        ),
        exact_replay=cast("bool | None", base_summary.get("requested_exact_replay")),
        input_snapshot_fingerprint=cast(
            "str | None", base_summary.get("input_snapshot_identity_fingerprint")
        ),
    )
    degraded_runtime_anchor_payload = {
        key: value
        for key, value in {
            "manifest_id": manifest.manifest_id,
            "effective_config_hash": base_summary.get("effective_config_hash"),
            "contract_ref": base_summary.get("contract_ref"),
            "contract_version": base_summary.get("contract_version"),
            "effective_config_artifact_id": base_summary.get(
                "effective_config_artifact_id"
            ),
        }.items()
        if value is not None
    }
    identity_graph = {
        "run_id": str(manifest.run_id),
        "manifest_id": manifest.manifest_id,
        "execution_fingerprint": manifest.execution_fingerprint,
        "effective_config_hash": base_summary.get("effective_config_hash"),
        "contract_ref": base_summary.get("contract_ref"),
        "contract_version": base_summary.get("contract_version"),
        "replay_of_run_id": base_summary.get("replay_of_run_id"),
        "replay_of_manifest_id": base_summary.get("replay_of_manifest_id"),
        "replay_parentage": base_summary.get("replay_parentage"),
        "replay_capability": base_summary.get("replay_capability"),
        "requested_exact_replay": base_summary.get("requested_exact_replay"),
        "exact_replay_support_boundary": base_summary.get(
            "exact_replay_support_boundary"
        ),
        "replay_capability_reason": base_summary.get("replay_capability_reason"),
        "exact_replay_eligible": base_summary.get("exact_replay_eligible"),
        "exact_replay_blockers": base_summary.get("exact_replay_blockers", []),
        "resume_contract": base_summary.get("resume_contract"),
        "resume_diagnostics": resume_diagnostics,
        "input_snapshot_ids": base_summary.get("input_snapshot_ids", []),
        "input_snapshot_content_hashes": base_summary.get(
            "input_snapshot_content_hashes",
            [],
        ),
        "input_snapshot_identity_fingerprint": base_summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "canonical_execution_identity": {
            "execution_fingerprint": manifest.execution_fingerprint,
            "payload": canonical_execution_identity_payload,
        },
        "degraded_runtime_anchor": {
            "compatibility_scope": "legacy_fallback_only",
            "fingerprint": (
                compute_execution_identity_fingerprint(degraded_runtime_anchor_payload)
                if degraded_runtime_anchor_payload
                else None
            ),
            "payload": degraded_runtime_anchor_payload,
        },
        "planned_artifacts": planned_artifacts,
        "published_artifacts": [
            _build_identity_graph_artifact_ref(artifact_ref)
            for artifact_ref in artifact_refs
        ],
        "occurrence_only_diagnostics": sorted(occurrence_only_diagnostic_scopes),
    }
    if "replay_mode" in base_summary:
        identity_graph["replay_mode"] = base_summary["replay_mode"]
        identity_graph["input_snapshot_count"] = base_summary["input_snapshot_count"]
        identity_graph["input_snapshots"] = base_summary["input_snapshots"]

    persistence_profile = _build_persistence_profile(
        base_summary=base_summary,
        ledger_entries_present=bool(ledger_entries),
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        missing_link_count=missing_link_count,
    )
    alert_signals = _build_alert_signals(
        latest_status=latest_entry.status,
        artifact_refs=artifact_refs,
        lineage_fragment_ids=lineage_fragment_ids,
        missing_link_count=missing_link_count,
        composite_resume_reconstructability_gap=_is_composite_execution_context(
            manifest
        ),
        dq_signal_present=dq_signal_present,
        cross_validation_signal_present=cross_validation_signal_present,
        required_persistence_profile_missing_requirements=cast(
            "list[str]",
            persistence_profile.get("required_profile_missing_requirements", []),
        ),
        replay_ready_missing_requirements=cast(
            "list[str]",
            persistence_profile.get("replay_ready_missing_requirements", []),
        ),
        forensic_grade_missing_requirements=cast(
            "list[str]",
            persistence_profile.get("forensic_grade_missing_requirements", []),
        ),
    )
    next_steps = _build_next_steps(alert_signals)
    summary = base_summary.copy()
    summary.update(
        {
            "total_events": len(ledger_entries),
            "latest_event_type": latest_entry.event_type,
            "latest_status": latest_entry.status,
            "event_family_counts": dict(sorted(family_counter.items())),
            "event_type_counts": dict(sorted(type_counter.items())),
            "artifact_refs": artifact_refs,
            "planned_artifact_count": len(manifest.planned_artifacts),
            "published_artifact_count": len(artifact_refs),
            "lineage_fragment_ids": sorted(lineage_fragment_ids),
            "missing_artifact_links": missing_link_count,
            "dq_rule_ids": sorted(dq_rule_ids),
            "dq_dispositions": sorted(dq_dispositions),
            "dq_report_paths": sorted(dq_report_paths),
            "dq_violation_kinds": sorted(dq_violation_kinds),
            "cross_validation_rule_ids": sorted(cross_validation_rule_ids),
            "cross_validation_config_paths": sorted(cross_validation_config_paths),
            "cross_validation_quarantine_policy": _resolve_policy_value(
                cross_validation_quarantine_policies
            ),
            "cross_validation_quarantine_replay_contract": _resolve_policy_value(
                cross_validation_replay_contracts
            ),
            "occurrence_only_diagnostics": sorted(occurrence_only_diagnostic_scopes),
            "resume_diagnostics": resume_diagnostics,
            "cross_validation_signal_present": cross_validation_signal_present,
            "correlation_anchor_gaps": correlation_anchor_gaps,
            "identity_graph_complete": (
                missing_link_count == 0
                and not any(correlation_anchor_gaps.values())
            ),
            "identity_graph": identity_graph,
            "persistence_profile": persistence_profile,
            "alert_signals": alert_signals,
            "next_steps": next_steps,
        }
    )
    return summary


def _build_identity_graph_artifact_ref(
    artifact_ref: dict[str, object],
) -> dict[str, object]:
    """Return the operator-facing artifact shape used inside identity graph."""
    return {
        key: value
        for key, value in artifact_ref.items()
        if key != "artifact_id"
    }


def _build_persistence_profile(
    *,
    base_summary: dict[str, object],
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
) -> dict[str, object]:
    """Classify the current run's persisted evidence against explicit profiles."""
    effective_config_artifact_present = bool(
        str(base_summary.get("effective_config_artifact_id") or "").strip()
    )
    immutable_input_snapshots_present = bool(base_summary.get("input_snapshot_ids", []))
    exact_replay_supported = bool(base_summary.get("exact_replay_eligible", False))
    exact_replay_boundary = str(
        base_summary.get("exact_replay_support_boundary")
        or "snapshot_backed_source_runs_only"
    )
    strict_replay_execution_context_supported = (
        exact_replay_boundary == "snapshot_backed_source_runs_only"
    )
    artifact_lineage_links_complete = not artifact_refs or (
        missing_link_count == 0 and bool(lineage_fragment_ids)
    )

    replay_ready_missing_requirements: list[str] = []
    if not strict_replay_execution_context_supported:
        replay_ready_missing_requirements.append(
            "strict_replay_execution_context_support"
        )
    if not exact_replay_supported:
        replay_ready_missing_requirements.append("exact_replay_capability")
    if not immutable_input_snapshots_present:
        replay_ready_missing_requirements.append("immutable_input_snapshots")
    if not effective_config_artifact_present:
        replay_ready_missing_requirements.append("effective_config_artifact")

    forensic_grade_missing_requirements = list(replay_ready_missing_requirements)
    if not ledger_entries_present:
        forensic_grade_missing_requirements.append("run_ledger_history")
    if not artifact_lineage_links_complete:
        forensic_grade_missing_requirements.append("artifact_lineage_links")

    required_profile = str(
        base_summary.get("required_persistence_profile") or "degraded_observable"
    )
    required_profile_missing_requirements: list[str]
    if required_profile == "forensic_grade":
        required_profile_missing_requirements = list(
            forensic_grade_missing_requirements
        )
    elif required_profile == "replay_ready":
        required_profile_missing_requirements = list(replay_ready_missing_requirements)
    else:
        required_profile = "degraded_observable"
        required_profile_missing_requirements = []

    attained_profile = "degraded_observable"
    if not replay_ready_missing_requirements:
        attained_profile = "replay_ready"
    if not forensic_grade_missing_requirements:
        attained_profile = "forensic_grade"

    return {
        "attained_profile": attained_profile,
        "required_profile": required_profile,
        "required_profile_satisfied": not required_profile_missing_requirements,
        "claims": {
            "degraded_observable": True,
            "replay_ready": not replay_ready_missing_requirements,
            "forensic_grade": not forensic_grade_missing_requirements,
        },
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
    }


def _build_alert_signals(
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
    artifact_ref_count = len(artifact_refs)
    has_artifact_refs = artifact_ref_count > 0
    immutable_input_snapshot_gap = (
        "immutable_input_snapshots" in replay_ready_missing_requirements
    )
    strict_replay_boundary_gap = (
        "strict_replay_execution_context_support"
        in replay_ready_missing_requirements
    )
    return {
        "run_failed": latest_status_normalized == "failed",
        "run_shutdown": latest_status_normalized == "shutdown",
        "artifact_linkage_gap": missing_link_count > 0,
        "lineage_gap": has_artifact_refs and not lineage_fragment_ids,
        "immutable_input_snapshot_gap": immutable_input_snapshot_gap,
        "strict_replay_boundary_gap": strict_replay_boundary_gap,
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


def _build_next_steps(alert_signals: dict[str, bool]) -> list[str]:
    """Return operator-oriented next steps based on active alert signals."""
    steps: list[str] = []
    if alert_signals.get("run_failed", False):
        steps.append(
            "Inspect failure classification and decide retry/quarantine/escalation."
        )
    if alert_signals.get("artifact_linkage_gap", False):
        steps.append(
            "Validate artifact publication metadata and repair dataset/lineage links."
        )
    if alert_signals.get("lineage_gap", False):
        steps.append(
            "Investigate lineage persistence for published artifacts before restart."
        )
    if alert_signals.get("immutable_input_snapshot_gap", False):
        steps.append(
            "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable."
        )
    if alert_signals.get("strict_replay_boundary_gap", False):
        steps.append(
            "Treat this execution context as outside the strict exact-replay "
            "support boundary; use rebuild/resume semantics instead of exact replay."
        )
    if alert_signals.get("required_persistence_profile_gap", False):
        steps.append(
            "Current persisted surfaces do not satisfy the declared required persistence profile for this run."
        )
    if alert_signals.get("composite_resume_reconstructability_gap", False):
        steps.append(
            "Treat composite resume as checkpoint snapshot plus ledger suffix "
            "replay only; do not expect per-provider result maps or other rich "
            "checkpoint payloads to be reconstructed."
        )
    if alert_signals.get("replay_ready_gap", False):
        steps.append(
            "Review replay-ready persistence requirements before treating this run as exact-replay capable."
        )
    if alert_signals.get("forensic_grade_gap", False):
        steps.append(
            "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction."
        )
    if alert_signals.get("dq_signal_present", False):
        steps.append(
            "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation."
        )
    if alert_signals.get("cross_validation_signal_present", False):
        steps.append(
            "Review cross-validation mismatch outcomes and composite policy anchors before retry or quarantine changes."
        )
    if alert_signals.get("run_shutdown", False):
        steps.append(
            "Confirm graceful shutdown reason and resume policy compatibility."
        )
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps
