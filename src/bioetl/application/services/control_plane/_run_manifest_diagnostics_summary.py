"""Summary assembly helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _resolve_policy_value,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_alert_signals,
    build_next_steps,
    build_persistence_profile,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _is_composite_execution_context,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
)


@dataclass(frozen=True, slots=True)
class _FinalSummaryRequest:
    """Structured input for final manifest diagnostics summary assembly."""

    manifest: RunManifest
    base_summary: dict[str, object]
    ledger_entries: tuple[RunLedgerEntry, ...]
    family_counter: Counter[str]
    type_counter: Counter[str]
    artifact_refs: list[dict[str, object]]
    lineage_fragment_ids: set[str]
    dq_rule_ids: set[str]
    dq_dispositions: set[str]
    dq_report_paths: set[str]
    dq_violation_kinds: set[str]
    cross_validation_rule_ids: set[str]
    cross_validation_config_paths: set[str]
    cross_validation_quarantine_policies: set[str]
    cross_validation_replay_contracts: set[str]
    occurrence_only_diagnostic_scopes: set[str]
    dq_signal_present: bool
    cross_validation_signal_present: bool
    missing_link_count: int
    correlation_anchor_gaps: dict[str, int]
    resume_diagnostics: dict[str, object] | None


def _build_final_summary(
    request: _FinalSummaryRequest,
) -> dict[str, object]:
    """Build final summary with all processed data."""
    latest_entry = request.ledger_entries[-1]
    planned_artifacts = cast(
        list[dict[str, object]],
        request.base_summary.get("planned_artifacts", []),
    )
    canonical_execution_identity_payload = build_execution_identity_payload(
        pipeline_name=request.manifest.pipeline_name,
        run_type=request.manifest.run_type.value,
        pipeline_version=cast(str | None, request.base_summary.get("pipeline_version")),
        effective_config_hash=cast(
            str | None, request.base_summary.get("effective_config_hash")
        ),
        dq_contract_compatibility_hash=cast(
            str | None,
            request.base_summary.get("dq_contract_compatibility_hash"),
        ),
        contract_ref=cast(str | None, request.base_summary.get("contract_ref")),
        contract_version=cast(str | None, request.base_summary.get("contract_version")),
        effective_config_artifact_id=cast(
            str | None,
            request.base_summary.get("effective_config_artifact_id"),
        ),
        exact_replay=cast(
            bool | None, request.base_summary.get("requested_exact_replay")
        ),
        input_snapshot_fingerprint=cast(
            str | None,
            request.base_summary.get("input_snapshot_identity_fingerprint"),
        ),
    )
    degraded_runtime_anchor_payload = {
        key: value
        for key, value in {
            "manifest_id": request.manifest.manifest_id,
            "effective_config_hash": request.base_summary.get("effective_config_hash"),
            "contract_ref": request.base_summary.get("contract_ref"),
            "contract_version": request.base_summary.get("contract_version"),
            "effective_config_artifact_id": request.base_summary.get(
                "effective_config_artifact_id"
            ),
        }.items()
        if value is not None
    }
    identity_graph = {
        "run_id": str(request.manifest.run_id),
        "manifest_id": request.manifest.manifest_id,
        "execution_fingerprint": request.manifest.execution_fingerprint,
        "config_hash": request.base_summary.get("config_hash"),
        "resolved_config_hash": request.base_summary.get("resolved_config_hash"),
        "effective_config_hash": request.base_summary.get("effective_config_hash"),
        "contract_ref": request.base_summary.get("contract_ref"),
        "contract_version": request.base_summary.get("contract_version"),
        "replay_of_run_id": request.base_summary.get("replay_of_run_id"),
        "replay_of_manifest_id": request.base_summary.get("replay_of_manifest_id"),
        "replay_parentage": request.base_summary.get("replay_parentage"),
        "replay_capability": request.base_summary.get("replay_capability"),
        "requested_exact_replay": request.base_summary.get("requested_exact_replay"),
        "exact_replay_support_boundary": request.base_summary.get(
            "exact_replay_support_boundary"
        ),
        "replay_family_contract": request.base_summary.get("replay_family_contract"),
        "replay_capability_reason": request.base_summary.get(
            "replay_capability_reason"
        ),
        "exact_replay_eligible": request.base_summary.get("exact_replay_eligible"),
        "exact_replay_blockers": request.base_summary.get("exact_replay_blockers", []),
        "resume_contract": request.base_summary.get("resume_contract"),
        "resume_diagnostics": request.resume_diagnostics,
        "lineage_closure_boundary": request.base_summary.get(
            "lineage_closure_boundary"
        ),
        "input_snapshot_ids": request.base_summary.get("input_snapshot_ids", []),
        "input_snapshot_content_hashes": request.base_summary.get(
            "input_snapshot_content_hashes",
            [],
        ),
        "input_snapshot_identity_fingerprint": request.base_summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "canonical_execution_identity": {
            "execution_fingerprint": request.manifest.execution_fingerprint,
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
            for artifact_ref in request.artifact_refs
        ],
        "occurrence_only_diagnostics": sorted(
            request.occurrence_only_diagnostic_scopes
        ),
    }
    if "replay_mode" in request.base_summary:
        identity_graph["replay_mode"] = request.base_summary["replay_mode"]
        identity_graph["input_snapshot_count"] = request.base_summary[
            "input_snapshot_count"
        ]
        identity_graph["input_snapshots"] = request.base_summary["input_snapshots"]

    persistence_profile = build_persistence_profile(
        base_summary=request.base_summary,
        ledger_entries_present=bool(request.ledger_entries),
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
        missing_link_count=request.missing_link_count,
    )
    alert_signals = build_alert_signals(
        latest_status=latest_entry.status,
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
        missing_link_count=request.missing_link_count,
        composite_resume_reconstructability_gap=_is_composite_execution_context(
            request.manifest
        ),
        dq_signal_present=request.dq_signal_present,
        cross_validation_signal_present=request.cross_validation_signal_present,
        required_persistence_profile_missing_requirements=cast(
            list[str],
            persistence_profile.get("required_profile_missing_requirements", []),
        ),
        replay_ready_missing_requirements=cast(
            list[str],
            persistence_profile.get("replay_ready_missing_requirements", []),
        ),
        forensic_grade_missing_requirements=cast(
            list[str],
            persistence_profile.get("forensic_grade_missing_requirements", []),
        ),
    )
    next_steps = build_next_steps(alert_signals)
    summary = request.base_summary.copy()
    summary.update(
        {
            "total_events": len(request.ledger_entries),
            "latest_event_type": latest_entry.event_type,
            "latest_status": latest_entry.status,
            "event_family_counts": dict(sorted(request.family_counter.items())),
            "event_type_counts": dict(sorted(request.type_counter.items())),
            "artifact_refs": request.artifact_refs,
            "planned_artifact_count": len(request.manifest.planned_artifacts),
            "published_artifact_count": len(request.artifact_refs),
            "lineage_fragment_ids": sorted(request.lineage_fragment_ids),
            "missing_artifact_links": request.missing_link_count,
            "dq_rule_ids": sorted(request.dq_rule_ids),
            "dq_dispositions": sorted(request.dq_dispositions),
            "dq_report_paths": sorted(request.dq_report_paths),
            "dq_violation_kinds": sorted(request.dq_violation_kinds),
            "cross_validation_rule_ids": sorted(request.cross_validation_rule_ids),
            "cross_validation_config_paths": sorted(
                request.cross_validation_config_paths
            ),
            "cross_validation_quarantine_policy": _resolve_policy_value(
                request.cross_validation_quarantine_policies
            ),
            "cross_validation_quarantine_replay_contract": _resolve_policy_value(
                request.cross_validation_replay_contracts
            ),
            "occurrence_only_diagnostics": sorted(
                request.occurrence_only_diagnostic_scopes
            ),
            "resume_diagnostics": request.resume_diagnostics,
            "cross_validation_signal_present": (
                request.cross_validation_signal_present
            ),
            "correlation_anchor_gaps": request.correlation_anchor_gaps,
            "identity_graph_complete": (
                request.missing_link_count == 0
                and not any(request.correlation_anchor_gaps.values())
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
    return {key: value for key, value in artifact_ref.items() if key != "artifact_id"}
