"""Diagnostics helpers for run manifest inspection service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_ledger import (
    _process_ledger_entries,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_alert_signals,
    build_lineage_closure_boundary,
    build_next_steps,
    build_persistence_profile,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_replay import (
    _build_replay_parentage,
    _build_resume_contract,
    _collect_append_mode_semantic_sinks,
    _collect_input_snapshot_content_hashes,
    _collect_input_snapshot_ids,
    _collect_input_snapshot_refs,
    _compute_input_snapshot_identity_fingerprint,
    _is_composite_execution_context,
    _resolve_exact_replay_blockers,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_capability_reason,
    _resolve_replay_family_contract,
    _resolve_replay_mode,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_summary import (
    _build_final_summary,
    _FinalSummaryRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


@dataclass(frozen=True, slots=True)
class _BaseSummaryReplayContext:
    """Replay- and resume-related inputs reused by base summary assembly."""

    requested_exact_replay: bool
    resume_requested: bool
    input_snapshots: list[dict[str, object]]
    replay_mode: str
    replay_capability_reason: str
    exact_replay_support_boundary: str
    exact_replay_blockers: list[str]
    resume_contract: dict[str, object]
    replay_family_contract: dict[str, object]


def _resolve_base_summary_replay_context(
    manifest: RunManifest,
) -> _BaseSummaryReplayContext:
    """Compute replay-derived context used by base summary assembly."""
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    resume_requested = bool(manifest.launch_context.get("resume"))
    input_snapshots = _collect_input_snapshot_refs(manifest)
    return _BaseSummaryReplayContext(
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        input_snapshots=input_snapshots,
        replay_mode=_resolve_replay_mode(
            manifest=manifest,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
        ),
        replay_capability_reason=_resolve_replay_capability_reason(
            manifest=manifest,
            input_snapshots=input_snapshots,
            resume_requested=resume_requested,
        ),
        exact_replay_support_boundary=_resolve_exact_replay_support_boundary(manifest),
        exact_replay_blockers=_resolve_exact_replay_blockers(
            manifest=manifest,
            input_snapshots=input_snapshots,
        ),
        resume_contract=_build_resume_contract(
            manifest=manifest,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
        ),
        replay_family_contract=_resolve_replay_family_contract(manifest),
    )


def _build_base_summary_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> dict[str, object]:
    """Return the manifest-derived payload before persistence overlays."""
    code_provenance = manifest.code_provenance
    strict_code_provenance_blockers: list[str] = []
    if not code_provenance.git_commit:
        strict_code_provenance_blockers.append("git_commit_missing")
    if str(code_provenance.source_revision_state or "").strip().lower() != "clean":
        strict_code_provenance_blockers.append("source_revision_state_not_clean")
    return {
        "manifest_id": manifest.manifest_id,
        "manifest_created_at": manifest.created_at.isoformat(),
        "run_id": str(manifest.run_id),
        "pipeline_name": manifest.pipeline_name,
        "provider": manifest.provider,
        "entity": manifest.entity,
        "execution_fingerprint": manifest.execution_fingerprint,
        "config_hash": code_provenance.config_hash,
        "resolved_config_hash": code_provenance.resolved_config_hash,
        "effective_config_hash": code_provenance.effective_config_hash,
        "pipeline_version": code_provenance.pipeline_version,
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "code_provenance_state": {
            "git_commit": code_provenance.git_commit,
            "source_revision_state": code_provenance.source_revision_state,
            "strict_code_provenance_ready": not strict_code_provenance_blockers,
            "strict_code_provenance_blockers": strict_code_provenance_blockers,
        },
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "dq_policy_ref": code_provenance.dq_policy_ref,
        "rule_bundle_version": code_provenance.rule_bundle_version,
        "dq_contract_compatibility_hash": (
            code_provenance.dq_contract_compatibility_hash
        ),
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
        "replay_parentage": _build_replay_parentage(manifest),
        "replay_capability": manifest.replay_capability.value,
        "required_persistence_profile": (
            str(manifest.launch_context.get("required_persistence_profile") or "")
            or "degraded_observable"
        ),
        "requested_exact_replay": replay_context.requested_exact_replay,
        "exact_replay_support_boundary": replay_context.exact_replay_support_boundary,
        "replay_capability_reason": replay_context.replay_capability_reason,
        "exact_replay_eligible": (
            manifest.replay_capability.value == "exact_replay_supported"
            and not replay_context.exact_replay_blockers
        ),
        "exact_replay_blockers": replay_context.exact_replay_blockers,
        "append_mode_semantic_sinks": _collect_append_mode_semantic_sinks(manifest),
        "input_snapshot_ids": _collect_input_snapshot_ids(
            replay_context.input_snapshots
        ),
        "input_snapshot_content_hashes": _collect_input_snapshot_content_hashes(
            replay_context.input_snapshots
        ),
        "input_snapshot_identity_fingerprint": (
            _compute_input_snapshot_identity_fingerprint(replay_context.input_snapshots)
        ),
        "replay_mode": replay_context.replay_mode,
        "replay_family_contract": replay_context.replay_family_contract,
        "resume_contract": replay_context.resume_contract,
        "resume_diagnostics": None,
        "lineage_closure_boundary": build_lineage_closure_boundary(
            provider=manifest.provider,
            entity=manifest.entity,
            contract_ref=code_provenance.contract_ref,
        ),
        "input_snapshot_count": len(replay_context.input_snapshots),
        "input_snapshots": replay_context.input_snapshots,
        "planned_artifacts": [
            {"layer": artifact.layer, "path": artifact.path}
            for artifact in manifest.planned_artifacts
        ],
        "occurrence_only_diagnostics": [],
    }


def _attach_base_summary_runtime_views(
    manifest: RunManifest,
    summary: dict[str, object],
) -> None:
    """Attach persistence, alert, and scoring overlays to base summary."""
    persistence_profile = build_persistence_profile(
        base_summary=summary,
        ledger_entries_present=False,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
    )
    summary["persistence_profile"] = persistence_profile
    summary["alert_signals"] = build_alert_signals(
        latest_status=None,
        artifact_refs=[],
        lineage_fragment_ids=set(),
        missing_link_count=0,
        composite_resume_reconstructability_gap=_is_composite_execution_context(
            manifest
        ),
        dq_signal_present=False,
        cross_validation_signal_present=False,
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
    summary["next_steps"] = build_next_steps(
        cast(dict[str, bool], summary["alert_signals"])
    )
    summary["reproducibility_audit_score"] = build_reproducibility_audit_scoring(
        summary
    )


def _build_base_summary(
    manifest: RunManifest,
) -> dict[str, object]:
    """Build base summary from manifest code provenance."""
    replay_context = _resolve_base_summary_replay_context(manifest)
    summary = _build_base_summary_payload(manifest, replay_context)
    _attach_base_summary_runtime_views(manifest, summary)
    return summary


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
        resume_diagnostics,
    ) = _process_ledger_entries(ledger_entries)

    return _build_final_summary(
        _FinalSummaryRequest(
            manifest=manifest,
            base_summary=base_summary,
            ledger_entries=ledger_entries,
            family_counter=family_counter,
            type_counter=type_counter,
            artifact_refs=artifact_refs,
            lineage_fragment_ids=lineage_fragment_ids,
            dq_rule_ids=dq_rule_ids,
            dq_dispositions=dq_dispositions,
            dq_report_paths=dq_report_paths,
            dq_violation_kinds=dq_violation_kinds,
            cross_validation_rule_ids=cross_validation_rule_ids,
            cross_validation_config_paths=cross_validation_config_paths,
            cross_validation_quarantine_policies=(cross_validation_quarantine_policies),
            cross_validation_replay_contracts=cross_validation_replay_contracts,
            occurrence_only_diagnostic_scopes=occurrence_only_diagnostic_scopes,
            dq_signal_present=dq_signal_present,
            cross_validation_signal_present=cross_validation_signal_present,
            missing_link_count=missing_link_count,
            correlation_anchor_gaps=correlation_anchor_gaps,
            resume_diagnostics=resume_diagnostics,
        )
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
    composite_resume_reconstructability_gap: bool,
    dq_signal_present: bool,
    cross_validation_signal_present: bool,
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
        "strict_replay_execution_context_support" in replay_ready_missing_requirements
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
        "replay_ready_gap": bool(replay_ready_missing_requirements),
        "forensic_grade_gap": bool(forensic_grade_missing_requirements),
        "dq_signal_present": dq_signal_present,
        "cross_validation_signal_present": cross_validation_signal_present,
    }


_NEXT_STEP_MAPPING = {
    "run_failed": "Inspect failure classification and decide retry/quarantine/escalation.",
    "artifact_linkage_gap": (
        "Validate artifact publication metadata and repair dataset/lineage links."
    ),
    "lineage_gap": "Investigate lineage persistence for published artifacts before restart.",
    "immutable_input_snapshot_gap": (
        "Persist immutable cached Bronze input snapshots before treating this run as "
        "strict exact-replay capable."
    ),
    "strict_replay_boundary_gap": (
        "Treat this execution context as outside the strict exact-replay support "
        "boundary; use rebuild/resume semantics instead of exact replay."
    ),
    "composite_resume_reconstructability_gap": (
        "Treat composite resume as checkpoint snapshot plus ledger suffix replay "
        "only; do not expect per-provider result maps or other rich checkpoint "
        "payloads to be reconstructed."
    ),
    "replay_ready_gap": (
        "Review replay-ready persistence requirements before treating this run as "
        "exact-replay capable."
    ),
    "forensic_grade_gap": (
        "Review forensic-grade persistence requirements before using this run for "
        "full trace/debug reconstruction."
    ),
    "dq_signal_present": (
        "Review DQ report artifacts, rule IDs, and contract policy anchors before "
        "retry or escalation."
    ),
    "cross_validation_signal_present": (
        "Review cross-validation mismatch outcomes and composite policy anchors "
        "before retry or quarantine changes."
    ),
    "run_shutdown": "Confirm graceful shutdown reason and resume policy compatibility.",
}


def _build_next_steps(alert_signals: dict[str, bool]) -> list[str]:
    """Return operator-oriented next steps based on active alert signals."""
    steps = [
        msg for key, msg in _NEXT_STEP_MAPPING.items() if alert_signals.get(key, False)
    ]
    if not steps:
        steps.append("No alert signals detected; continue routine monitoring.")
    return steps


__all__ = ["build_diagnostics_summary"]
