"""Summary assembly helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_composite import (
    build_composite_dossier_projection,
)
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
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
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


def _sorted_text_items(value: object) -> list[str]:
    """Return unique text items in stable content order."""
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    return sorted({text for item in value if (text := str(item).strip())})


def _artifact_ref_sort_key(artifact_ref: dict[str, object]) -> tuple[str, ...]:
    """Return a stable ordering key for concrete produced artifacts."""
    return (
        str(artifact_ref.get("stage") or ""),
        str(artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id") or ""),
        str(artifact_ref.get("lineage_fragment_id") or ""),
        str(artifact_ref.get("artifact_path") or ""),
        str(artifact_ref.get("event_type") or ""),
    )


def _build_trace_artifact_ref(
    artifact_ref: dict[str, object],
) -> dict[str, object]:
    """Return the concrete produced-artifact shape used by replay trace output."""
    ordered_keys = (
        "event_type",
        "stage",
        "artifact_id",
        "dataset_ref",
        "lineage_fragment_id",
        "artifact_path",
        "metadata_path",
        "artifact_kind",
        "record_count",
        "total_bytes",
        "pipeline_name",
        "provider",
        "entity",
        "run_id",
        "manifest_id",
    )
    return {
        key: artifact_ref[key]
        for key in ordered_keys
        if key in artifact_ref and artifact_ref[key] is not None
    }


def _build_produced_artifact_trace(
    *,
    manifest: RunManifest,
    ledger_entries_present: bool,
    artifact_refs: list[dict[str, object]],
) -> dict[str, object]:
    """Return the manifest-id rooted concrete produced-artifact trace."""
    artifacts = [
        _build_trace_artifact_ref(artifact_ref)
        for artifact_ref in sorted(artifact_refs, key=_artifact_ref_sort_key)
    ]
    missing_requirements: list[str] = []
    if not ledger_entries_present:
        missing_requirements.append("run_ledger_history")
    if not artifacts:
        missing_requirements.append("artifact_publication_event")
    return {
        "lookup": "run_ledger_by_manifest_id",
        "lookup_key": manifest.manifest_id,
        "manifest_id": manifest.manifest_id,
        "complete": not missing_requirements,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "missing_requirements": missing_requirements,
    }


def _build_exact_replay_anchors(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str] | frozenset[str],
) -> dict[str, object]:
    """Return semantic replay anchors separately from occurrence diagnostics."""
    published_artifact_ids = _sorted_text_items(
        [
            artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id")
            for artifact_ref in artifact_refs
        ]
    )
    published_artifact_paths = _sorted_text_items(
        [artifact_ref.get("artifact_path") for artifact_ref in artifact_refs]
    )
    anchors: dict[str, object] = {
        "semantic_identity_anchor": "execution_fingerprint",
        "execution_fingerprint": manifest.execution_fingerprint,
        "pipeline_name": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "pipeline_version": summary.get("pipeline_version"),
        "git_commit": summary.get("git_commit"),
        "dependency_lock_state": summary.get("dependency_lock_state"),
        "effective_config_hash": summary.get("effective_config_hash"),
        "dq_contract_compatibility_hash": summary.get("dq_contract_compatibility_hash"),
        "contract_ref": summary.get("contract_ref"),
        "contract_version": summary.get("contract_version"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_identity_fingerprint": summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "input_snapshot_ids": _sorted_text_items(summary.get("input_snapshot_ids", [])),
        "input_snapshot_content_hashes": _sorted_text_items(
            summary.get("input_snapshot_content_hashes", [])
        ),
        "published_artifact_ids": published_artifact_ids,
        "published_artifact_paths": published_artifact_paths,
        "lineage_fragment_ids": sorted(lineage_fragment_ids),
    }
    if summary.get("dependency_lock_hash") is not None:
        anchors["dependency_lock_hash"] = summary.get("dependency_lock_hash")
    return anchors


def _build_canonical_execution_identity(
    request: _FinalSummaryRequest,
) -> dict[str, object]:
    """Return the canonical execution identity payload for the summary graph."""
    return cast(
        dict[str, object],
        build_execution_identity_payload(
            pipeline_name=request.manifest.pipeline_name,
            run_type=request.manifest.run_type.value,
            pipeline_version=cast(
                str | None, request.base_summary.get("pipeline_version")
            ),
            git_commit=cast(str | None, request.base_summary.get("git_commit")),
            effective_config_hash=cast(
                str | None, request.base_summary.get("effective_config_hash")
            ),
            dq_contract_compatibility_hash=cast(
                str | None,
                request.base_summary.get("dq_contract_compatibility_hash"),
            ),
            contract_ref=cast(str | None, request.base_summary.get("contract_ref")),
            contract_version=cast(
                str | None, request.base_summary.get("contract_version")
            ),
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
        ),
    )


def _build_degraded_runtime_anchor_payload(
    request: _FinalSummaryRequest,
) -> dict[str, object]:
    """Return the degraded runtime anchor payload used for fallback identity."""
    return {
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


def _add_identity_graph_optional_fields(
    identity_graph: dict[str, object],
    request: _FinalSummaryRequest,
) -> None:
    """Add optional identity graph fields without changing historical shape."""
    if request.base_summary.get("dependency_lock_hash") is not None:
        identity_graph["dependency_lock_hash"] = request.base_summary.get(
            "dependency_lock_hash"
        )
    if "replay_mode" not in request.base_summary:
        return
    identity_graph["operator_replay_mode"] = request.base_summary.get(
        "operator_replay_mode"
    )
    identity_graph["replay_mode"] = request.base_summary["replay_mode"]
    identity_graph["continuation_mode"] = request.base_summary.get(
        "continuation_mode"
    )
    identity_graph["input_snapshot_count"] = request.base_summary[
        "input_snapshot_count"
    ]
    identity_graph["snapshot_status"] = request.base_summary.get("snapshot_status")
    identity_graph["input_snapshots"] = request.base_summary["input_snapshots"]


def _build_identity_graph(
    request: _FinalSummaryRequest,
    *,
    exact_replay_anchors: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Assemble the operator-facing run identity graph for final summary."""
    planned_artifacts = cast(
        list[dict[str, object]],
        request.base_summary.get("planned_artifacts", []),
    )
    canonical_execution_identity_payload = _build_canonical_execution_identity(request)
    degraded_runtime_anchor_payload = _build_degraded_runtime_anchor_payload(request)
    identity_graph = {
        "run_id": str(request.manifest.run_id),
        "manifest_id": request.manifest.manifest_id,
        "execution_fingerprint": request.manifest.execution_fingerprint,
        "config_hash": request.base_summary.get("config_hash"),
        "resolved_config_hash": request.base_summary.get("resolved_config_hash"),
        "effective_config_hash": request.base_summary.get("effective_config_hash"),
        "git_commit": request.base_summary.get("git_commit"),
        "source_revision_state": request.base_summary.get("source_revision_state"),
        "dependency_lock_state": request.base_summary.get("dependency_lock_state"),
        "code_provenance_state": request.base_summary.get("code_provenance_state"),
        "contract_ref": request.base_summary.get("contract_ref"),
        "contract_version": request.base_summary.get("contract_version"),
        "replay_of_run_id": request.base_summary.get("replay_of_run_id"),
        "replay_of_manifest_id": request.base_summary.get("replay_of_manifest_id"),
        "replay_parentage": request.base_summary.get("replay_parentage"),
        "replay_capability": request.base_summary.get("replay_capability"),
        "operator_replay_mode": request.base_summary.get("operator_replay_mode"),
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
        "append_mode_semantic_sinks": request.base_summary.get(
            "append_mode_semantic_sinks",
            [],
        ),
        "resume_contract": request.base_summary.get("resume_contract"),
        "resume_diagnostics": request.resume_diagnostics,
        "lineage_closure_boundary": request.base_summary.get(
            "lineage_closure_boundary"
        ),
        "input_snapshot_ids": request.base_summary.get("input_snapshot_ids", []),
        "snapshot_status": request.base_summary.get("snapshot_status"),
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
        "exact_replay_anchors": exact_replay_anchors,
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
        "produced_artifact_trace": produced_artifact_trace,
        "occurrence_only_diagnostics": sorted(
            request.occurrence_only_diagnostic_scopes
        ),
    }
    _add_identity_graph_optional_fields(identity_graph, request)
    return identity_graph


def _build_alert_bundle(
    request: _FinalSummaryRequest,
    *,
    persistence_profile: dict[str, object],
) -> tuple[dict[str, bool], list[str]]:
    """Return alert signals and operator next steps for final summary."""
    latest_entry = request.ledger_entries[-1]
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
    return alert_signals, build_next_steps(alert_signals)


def _build_final_summary_updates(
    request: _FinalSummaryRequest,
    *,
    identity_graph: dict[str, object],
    persistence_profile: dict[str, object],
    composite_dossier_projection: dict[str, object],
    alert_signals: dict[str, bool],
    next_steps: list[str],
    exact_replay_anchors: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Return the summary update payload layered onto the base summary."""
    latest_entry = request.ledger_entries[-1]
    return {
        "total_events": len(request.ledger_entries),
        "latest_event_type": latest_entry.event_type,
        "latest_status": latest_entry.status,
        "event_family_counts": dict(sorted(request.family_counter.items())),
        "event_type_counts": dict(sorted(request.type_counter.items())),
        "artifact_refs": request.artifact_refs,
        "exact_replay_anchors": exact_replay_anchors,
        "produced_artifact_trace": produced_artifact_trace,
        "planned_artifact_count": len(request.manifest.planned_artifacts),
        "published_artifact_count": len(request.artifact_refs),
        "lineage_fragment_ids": sorted(request.lineage_fragment_ids),
        "missing_artifact_links": request.missing_link_count,
        "dq_rule_ids": sorted(request.dq_rule_ids),
        "dq_dispositions": sorted(request.dq_dispositions),
        "dq_report_paths": sorted(request.dq_report_paths),
        "dq_violation_kinds": sorted(request.dq_violation_kinds),
        "cross_validation_rule_ids": sorted(request.cross_validation_rule_ids),
        "cross_validation_config_paths": sorted(request.cross_validation_config_paths),
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
        "composite_dossier_projection": composite_dossier_projection,
        "cross_validation_signal_present": request.cross_validation_signal_present,
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


def _build_final_summary(
    request: _FinalSummaryRequest,
) -> dict[str, object]:
    """Build final summary with all processed data."""
    exact_replay_anchors = _build_exact_replay_anchors(
        manifest=request.manifest,
        summary=request.base_summary,
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
    )
    produced_artifact_trace = _build_produced_artifact_trace(
        manifest=request.manifest,
        ledger_entries_present=bool(request.ledger_entries),
        artifact_refs=request.artifact_refs,
    )
    identity_graph = _build_identity_graph(
        request,
        exact_replay_anchors=exact_replay_anchors,
        produced_artifact_trace=produced_artifact_trace,
    )
    persistence_profile = build_persistence_profile(
        base_summary=request.base_summary,
        ledger_entries_present=bool(request.ledger_entries),
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
        missing_link_count=request.missing_link_count,
    )
    composite_dossier_projection = build_composite_dossier_projection(
        request,
        persistence_profile=persistence_profile,
    )
    alert_signals, next_steps = _build_alert_bundle(
        request,
        persistence_profile=persistence_profile,
    )
    summary = request.base_summary.copy()
    summary.update(
        _build_final_summary_updates(
            request,
            identity_graph=identity_graph,
            persistence_profile=persistence_profile,
            composite_dossier_projection=composite_dossier_projection,
            alert_signals=alert_signals,
            next_steps=next_steps,
            exact_replay_anchors=exact_replay_anchors,
            produced_artifact_trace=produced_artifact_trace,
        )
    )
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )
    return summary


def _build_identity_graph_artifact_ref(
    artifact_ref: dict[str, object],
) -> dict[str, object]:
    """Return the operator-facing artifact shape used inside identity graph."""
    return {key: value for key, value in artifact_ref.items() if key != "artifact_id"}
