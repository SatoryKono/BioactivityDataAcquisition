"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_helpers import (
    extract_dq_details,
    update_correlation_anchor_gaps,
)
from bioetl.domain.control_plane import ReplayCapability, RunLedgerEntry, RunManifest
from bioetl.domain.normalization import (
    build_execution_identity_payload,
    compute_execution_identity_fingerprint,
    serialize_json_canonical,
)


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    code_provenance = manifest.code_provenance
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    resume_requested = bool(manifest.launch_context.get("resume"))
    input_snapshots = _collect_input_snapshot_refs(manifest)
    replay_mode = _resolve_replay_mode(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
    )
    replay_capability_reason = _resolve_replay_capability_reason(
        manifest=manifest,
        input_snapshots=input_snapshots,
        resume_requested=resume_requested,
    )
    exact_replay_support_boundary = _resolve_exact_replay_support_boundary(manifest)
    exact_replay_blockers = _resolve_exact_replay_blockers(
        manifest=manifest,
        input_snapshots=input_snapshots,
    )
    summary: dict[str, object] = {
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "pipeline_name": manifest.pipeline_name,
        "provider": manifest.provider,
        "entity": manifest.entity,
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": code_provenance.config_hash,
        "effective_config_hash": code_provenance.config_hash,
        "pipeline_version": code_provenance.pipeline_version,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "dq_contract_compatibility_hash": (
            code_provenance.dq_contract_compatibility_hash
        ),
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
        "replay_capability": manifest.replay_capability.value,
        "requested_exact_replay": requested_exact_replay,
        "exact_replay_support_boundary": exact_replay_support_boundary,
        "replay_capability_reason": replay_capability_reason,
        "exact_replay_eligible": (
            manifest.replay_capability.value == "exact_replay_supported"
        ),
        "exact_replay_blockers": exact_replay_blockers,
        "input_snapshot_ids": _collect_input_snapshot_ids(input_snapshots),
        "input_snapshot_content_hashes": _collect_input_snapshot_content_hashes(
            input_snapshots
        ),
        "input_snapshot_identity_fingerprint": (
            _compute_input_snapshot_identity_fingerprint(input_snapshots)
        ),
        "replay_mode": replay_mode,
        "input_snapshot_count": len(input_snapshots),
        "input_snapshots": input_snapshots,
        "planned_artifacts": [
            {"layer": artifact.layer, "path": artifact.path}
            for artifact in manifest.planned_artifacts
        ],
        "occurrence_only_diagnostics": [],
    }
    persistence_profile = _build_persistence_profile(
        base_summary=summary,
        ledger_entries_present=False,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
    )
    summary["persistence_profile"] = persistence_profile
    summary["alert_signals"] = _build_alert_signals(
        latest_status=None,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
        dq_signal_present=False,
        cross_validation_signal_present=False,
        replay_ready_missing_requirements=cast(
            "list[str]",
            persistence_profile.get("replay_ready_missing_requirements", []),
        ),
        forensic_grade_missing_requirements=cast(
            "list[str]",
            persistence_profile.get("forensic_grade_missing_requirements", []),
        ),
    )
    summary["next_steps"] = _build_next_steps(
        cast("dict[str, bool]", summary["alert_signals"])
    )
    return summary


def _resolve_replay_mode(
    *,
    manifest: RunManifest,
    requested_exact_replay: bool,
    resume_requested: bool,
) -> str:
    """Resolve operator-facing replay mode from manifest intent and capability."""
    if (
        requested_exact_replay
        and manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        return "exact_replay"
    if manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return "snapshot_backed_run"
    if resume_requested or manifest.replay_capability == ReplayCapability.RESUME_ONLY:
        return "resume"
    return "live_fetch"


def _resolve_replay_capability_reason(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    resume_requested: bool,
) -> str:
    """Return one operator-facing explanation for replay capability."""
    if _is_composite_execution_context(manifest):
        return "exact_replay_not_supported_for_composite_execution"
    if (
        manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        and input_snapshots
    ):
        return "immutable_input_snapshots_present"
    if manifest.replay_capability == ReplayCapability.RESUME_ONLY or resume_requested:
        return "resume_requested_without_snapshot_backed_inputs"
    return "immutable_input_snapshots_missing"


def _resolve_exact_replay_blockers(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return explicit blockers preventing exact replay eligibility."""
    if manifest.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return []
    blockers: list[str] = []
    if _is_composite_execution_context(manifest):
        blockers.append("exact_replay_not_supported_for_composite_execution")
    if not input_snapshots:
        blockers.append("immutable_input_snapshots_missing")
    return blockers


def _resolve_exact_replay_support_boundary(manifest: RunManifest) -> str:
    """Return the supported exact-replay boundary for one manifested run."""
    if _is_composite_execution_context(manifest):
        return "composite_execution_unsupported"
    return "snapshot_backed_source_runs_only"


def _is_composite_execution_context(manifest: RunManifest) -> bool:
    """Return whether the manifest represents composite execution."""
    execution_context = str(manifest.launch_context.get("execution_context") or "")
    return execution_context == "composite" or manifest.provider == "composite"


def _process_ledger_entries(
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> tuple[
    Counter[str],
    Counter[str],
    list[dict[str, object]],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    set[str],
    bool,
    bool,
    int,
    dict[str, int],
]:
    """Process ledger entries and extract statistics."""
    family_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    artifact_refs: list[dict[str, object]] = []
    lineage_fragment_ids: set[str] = set()
    dq_rule_ids: set[str] = set()
    dq_dispositions: set[str] = set()
    dq_report_paths: set[str] = set()
    dq_violation_kinds: set[str] = set()
    cross_validation_rule_ids: set[str] = set()
    cross_validation_config_paths: set[str] = set()
    cross_validation_quarantine_policies: set[str] = set()
    cross_validation_replay_contracts: set[str] = set()
    occurrence_only_diagnostic_scopes: set[str] = set()
    dq_signal_present = False
    cross_validation_signal_present = False
    missing_link_count = 0
    correlation_anchor_gaps = {
        "effective_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }

    for entry in ledger_entries:
        family_counter.update([entry.event_family or "diagnostic"])
        type_counter.update([entry.event_type])
        artifact_ref = _build_artifact_ref(entry)
        if artifact_ref is not None:
            artifact_refs.append(artifact_ref)
            if (
                artifact_ref.get("dataset_ref") is None
                and artifact_ref.get("lineage_fragment_id") is None
            ):
                missing_link_count += 1
        if entry.lineage_fragment_id:
            lineage_fragment_ids.add(entry.lineage_fragment_id)
        dq_details = extract_dq_details(entry)
        dq_rule_ids.update(dq_details["rule_ids"])
        dq_dispositions.update(dq_details["dispositions"])
        dq_report_paths.update(dq_details["report_paths"])
        dq_violation_kinds.update(dq_details["violation_kinds"])
        cross_validation_rule_ids.update(dq_details["cross_validation_rule_ids"])
        cross_validation_config_paths.update(
            dq_details["cross_validation_config_paths"]
        )
        cross_validation_quarantine_policies.update(
            dq_details["cross_validation_quarantine_policies"]
        )
        cross_validation_replay_contracts.update(
            dq_details["cross_validation_replay_contracts"]
        )
        occurrence_only_diagnostic_scopes.update(
            dq_details["occurrence_only_diagnostic_scopes"]
        )
        dq_signal_present = dq_signal_present or dq_details["has_signal"]
        cross_validation_signal_present = (
            cross_validation_signal_present or dq_details["has_cross_validation_signal"]
        )
        update_correlation_anchor_gaps(
            correlation_anchor_gaps,
            entry,
        )

    return (
        family_counter,
        type_counter,
        artifact_refs,
        lineage_fragment_ids,
        dq_rule_ids,
        dq_dispositions,
        dq_report_paths,
        dq_violation_kinds,
        cross_validation_rule_ids,
        cross_validation_config_paths,
        cross_validation_quarantine_policies,
        cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes,
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
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
        "replay_capability": base_summary.get("replay_capability"),
        "requested_exact_replay": base_summary.get("requested_exact_replay"),
        "exact_replay_support_boundary": base_summary.get(
            "exact_replay_support_boundary"
        ),
        "replay_capability_reason": base_summary.get("replay_capability_reason"),
        "exact_replay_eligible": base_summary.get("exact_replay_eligible"),
        "exact_replay_blockers": base_summary.get("exact_replay_blockers", []),
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
        dq_signal_present=dq_signal_present,
        cross_validation_signal_present=cross_validation_signal_present,
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

    attained_profile = "degraded_observable"
    if not replay_ready_missing_requirements:
        attained_profile = "replay_ready"
    if not forensic_grade_missing_requirements:
        attained_profile = "forensic_grade"

    return {
        "attained_profile": attained_profile,
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
        "replay_ready_missing_requirements": replay_ready_missing_requirements,
        "forensic_grade_missing_requirements": forensic_grade_missing_requirements,
        "composite_resume_reconstructability": {
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


def _collect_input_snapshot_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return deterministic flattened snapshot provenance extracted from source refs."""
    refs: list[dict[str, object]] = []
    for source_ref in manifest.source_refs:
        for snapshot in source_ref.input_snapshots:
            refs.append(
                {
                    "provider": source_ref.provider,
                    "entity": source_ref.entity,
                    "pipeline_name": source_ref.pipeline_name,
                    "query": source_ref.query,
                    "snapshot_id": snapshot.snapshot_id,
                    "content_hash": snapshot.content_hash,
                    "immutable_uri": snapshot.immutable_uri,
                    "query_fingerprint": snapshot.query_fingerprint,
                    "etag": snapshot.etag,
                    "last_modified": snapshot.last_modified,
                    "captured_at": snapshot.captured_at.isoformat()
                    if snapshot.captured_at is not None
                    else None,
                }
            )
    refs.sort(
        key=lambda item: (
            str(item.get("provider") or ""),
            str(item.get("entity") or ""),
            str(item.get("pipeline_name") or ""),
            str(item.get("snapshot_id") or ""),
        )
    )
    return refs


def _collect_input_snapshot_ids(input_snapshots: list[dict[str, object]]) -> list[str]:
    """Return deterministic snapshot identities for resume/exact-replay anchors."""
    return [
        str(snapshot_id)
        for snapshot_id in (
            snapshot.get("snapshot_id") for snapshot in input_snapshots
        )
        if snapshot_id is not None
    ]


def _collect_input_snapshot_content_hashes(
    input_snapshots: list[dict[str, object]],
) -> list[str]:
    """Return deterministic snapshot content hashes for operator inspection."""
    return [
        str(content_hash)
        for content_hash in (
            snapshot.get("content_hash") for snapshot in input_snapshots
        )
        if content_hash is not None
    ]


def _compute_input_snapshot_identity_fingerprint(
    input_snapshots: list[dict[str, object]],
) -> str | None:
    """Compute the same stable replay-anchor fingerprint shape used by checkpoints."""
    snapshot_ids = _collect_input_snapshot_ids(input_snapshots)
    if not snapshot_ids:
        return None
    encoded = serialize_json_canonical(snapshot_ids)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_diagnostics_summary(
    manifest: RunManifest,
    ledger_entries: tuple[RunLedgerEntry, ...],
) -> dict[str, object]:
    """Build compact operator-oriented diagnostics summary."""
    base_summary = _build_base_summary(manifest)

    if not ledger_entries:
        return base_summary

    (
        family_counter,
        type_counter,
        artifact_refs,
        lineage_fragment_ids,
        dq_rule_ids,
        dq_dispositions,
        dq_report_paths,
        dq_violation_kinds,
        cross_validation_rule_ids,
        cross_validation_config_paths,
        cross_validation_quarantine_policies,
        cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes,
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
    ) = _process_ledger_entries(ledger_entries)

    return _build_final_summary(
        manifest,
        base_summary,
        ledger_entries,
        family_counter,
        type_counter,
        artifact_refs,
        lineage_fragment_ids,
        dq_rule_ids,
        dq_dispositions,
        dq_report_paths,
        dq_violation_kinds,
        cross_validation_rule_ids,
        cross_validation_config_paths,
        cross_validation_quarantine_policies,
        cross_validation_replay_contracts,
        occurrence_only_diagnostic_scopes,
        dq_signal_present,
        cross_validation_signal_present,
        missing_link_count,
        correlation_anchor_gaps,
    )


def _build_artifact_ref(entry: RunLedgerEntry) -> dict[str, object] | None:
    if entry.event_family != "artifact" and entry.event_type != "artifact_published":
        return None
    details = entry.details or {}
    artifact_path = details.get("artifact_path")
    artifact_ref: dict[str, object] = {
        "event_type": entry.event_type,
        "stage": entry.stage,
        "artifact_id": entry.dataset_ref,
        "dataset_ref": entry.dataset_ref,
        "lineage_fragment_id": entry.lineage_fragment_id,
        "artifact_path": None if artifact_path is None else str(artifact_path),
    }
    for detail_key in (
        "metadata_path",
        "artifact_kind",
        "record_count",
        "total_bytes",
        "pipeline_name",
        "provider",
        "entity",
        "run_id",
        "manifest_id",
    ):
        detail_value = details.get(detail_key)
        if detail_value is not None:
            artifact_ref[detail_key] = detail_value
    return artifact_ref


def _resolve_policy_value(values: set[str]) -> str | None:
    """Return one canonical policy value or an explicit mixed-policy marker."""
    if not values:
        return None
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def _build_alert_signals(
    *,
    latest_status: str | None,
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str],
    missing_link_count: int,
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
    replay_ready_missing_requirements: list[str],
    forensic_grade_missing_requirements: list[str],
) -> dict[str, bool]:
    """Map diagnostics summary to alert-oriented boolean signals."""
    latest_status_normalized = (latest_status or "").strip().lower()
    artifact_ref_count = len(artifact_refs)
    has_artifact_refs = artifact_ref_count > 0
    strict_replay_boundary_gap = (
        "strict_replay_execution_context_support"
        in replay_ready_missing_requirements
    )
    return {
        "run_failed": latest_status_normalized == "failed",
        "run_shutdown": latest_status_normalized == "shutdown",
        "artifact_linkage_gap": missing_link_count > 0,
        "lineage_gap": has_artifact_refs and not lineage_fragment_ids,
        "strict_replay_boundary_gap": strict_replay_boundary_gap,
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
    if alert_signals.get("strict_replay_boundary_gap", False):
        steps.append(
            "Treat this execution context as outside the strict exact-replay support boundary; use rebuild/resume semantics instead of exact replay."
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


__all__ = ["build_diagnostics_summary"]
