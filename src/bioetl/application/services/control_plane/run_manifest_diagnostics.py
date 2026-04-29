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
    _assess_manifest_reproducibility_policy,
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
    _build_exact_replay_anchors,
    _build_final_summary,
    _build_produced_artifact_trace,
    _FinalSummaryRequest,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


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
    policy_assessment: ReproducibilityPolicyAssessment


_EMPTY_RESUME_ANCHOR_COMPARISON = {
    "checkpoint_identity_present": False,
    "matching_fields": [],
    "mismatched_fields": [],
    "missing_current_fields": [],
    "missing_checkpoint_fields": [],
}


def _resolve_resume_identity_maps(
    summary: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]] | None:
    resume_diagnostics = summary.get("resume_diagnostics")
    if not isinstance(resume_diagnostics, dict):
        return None
    current_identity = resume_diagnostics.get("current_identity")
    checkpoint_identity = resume_diagnostics.get("checkpoint_identity")
    if not isinstance(current_identity, dict) or not isinstance(
        checkpoint_identity, dict
    ):
        return None
    return current_identity, checkpoint_identity


def _resolve_base_summary_replay_context(
    manifest: RunManifest,
) -> _BaseSummaryReplayContext:
    """Compute replay-derived context used by base summary assembly."""
    requested_exact_replay = bool(manifest.launch_context.get("exact_replay"))
    resume_requested = bool(manifest.launch_context.get("resume"))
    input_snapshots = _collect_input_snapshot_refs(manifest)
    replay_family_contract = _resolve_replay_family_contract(manifest)
    policy_assessment = _assess_manifest_reproducibility_policy(
        manifest=manifest,
        requested_exact_replay=requested_exact_replay,
        resume_requested=resume_requested,
        replay_family_contract=replay_family_contract,
    )
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
            policy_assessment=policy_assessment,
        ),
        resume_contract=_build_resume_contract(
            manifest=manifest,
            requested_exact_replay=requested_exact_replay,
            resume_requested=resume_requested,
            policy_assessment=policy_assessment,
        ),
        replay_family_contract=replay_family_contract,
        policy_assessment=policy_assessment,
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
    summary: dict[str, object] = {
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
            replay_context.policy_assessment.required_persistence_profile
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
        "reproducibility_policy_assessment": (
            replay_context.policy_assessment.to_dict()
        ),
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
    summary["artifact_refs"] = []
    summary["lineage_fragment_ids"] = []
    summary["published_artifact_count"] = 0
    summary["exact_replay_anchors"] = _build_exact_replay_anchors(
        manifest=manifest,
        summary=summary,
        artifact_refs=[],
        lineage_fragment_ids=frozenset(),
    )
    summary["produced_artifact_trace"] = _build_produced_artifact_trace(
        manifest=manifest,
        ledger_entries_present=False,
        artifact_refs=[],
    )
    return summary


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
    summary["reproducibility_diagnostics"] = _build_unified_reproducibility_diagnostics(
        summary
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


def _build_unified_reproducibility_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    """Return a single operator-facing reproducibility diagnostics surface."""
    persistence_profile = cast(
        "dict[str, object]", summary.get("persistence_profile", {})
    )
    produced_artifact_trace = cast(
        "dict[str, object]",
        summary.get("produced_artifact_trace", {}),
    )
    return {
        "policy": {
            "required_persistence_profile": summary.get("required_persistence_profile"),
            "attained_profile": persistence_profile.get("attained_profile"),
            "required_profile_satisfied": persistence_profile.get(
                "required_profile_satisfied"
            ),
            "required_profile_missing_requirements": persistence_profile.get(
                "required_profile_missing_requirements",
                [],
            ),
            "replay_capability": summary.get("replay_capability"),
            "replay_mode": summary.get("replay_mode"),
            "replay_family_contract": summary.get("replay_family_contract"),
            "exact_replay_support_boundary": summary.get(
                "exact_replay_support_boundary"
            ),
            "exact_replay_blockers": summary.get("exact_replay_blockers", []),
            "policy_assessment": summary.get(
                "reproducibility_policy_assessment",
                {},
            ),
        },
        "semantic_identity": {
            "execution_fingerprint": summary.get("execution_fingerprint"),
            "config_hash_compatibility_anchor": summary.get("config_hash"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "input_snapshot_identity_fingerprint": summary.get(
                "input_snapshot_identity_fingerprint"
            ),
            "input_snapshot_ids": summary.get("input_snapshot_ids", []),
        },
        "effective_config": _build_effective_config_diagnostics(summary),
        "occurrence_identity": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
            "occurrence_only_diagnostics": summary.get(
                "occurrence_only_diagnostics",
                [],
            ),
        },
        "checkpoint_anchors": {
            "resume_contract": summary.get("resume_contract"),
            "resume_diagnostics": summary.get("resume_diagnostics"),
            "current_manifest_anchors": _build_current_checkpoint_anchor_payload(
                summary
            ),
            "resume_anchor_comparison": _build_resume_anchor_comparison(summary),
        },
        "lineage": {
            "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
            "lineage_fragment_ids": summary.get("lineage_fragment_ids", []),
            "planned_artifact_count": summary.get("planned_artifact_count"),
            "published_artifact_count": summary.get("published_artifact_count"),
            "produced_artifact_trace_complete": produced_artifact_trace.get("complete"),
        },
    }


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    """Return semantic-vs-occurrence effective-config diagnostics."""
    return {
        "semantic": {
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "config_hash_compatibility_anchor": summary.get("config_hash"),
        },
        "occurrence": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
        },
        "diff_policy": {
            "semantic_anchor": "effective_config_hash",
            "occurrence_fields": [
                "run_id",
                "manifest_id",
                "manifest_created_at",
            ],
            "config_hash_policy": "legacy_alias_for_resolved_config_hash",
        },
    }


def _build_current_checkpoint_anchor_payload(
    summary: dict[str, object],
) -> dict[str, object]:
    """Return current manifest anchors used for checkpoint comparisons."""
    return {
        "execution_fingerprint": summary.get("execution_fingerprint"),
        "manifest_id": summary.get("manifest_id"),
        "effective_config_hash": summary.get("effective_config_hash"),
        "contract_ref": summary.get("contract_ref"),
        "contract_version": summary.get("contract_version"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_ids": summary.get("input_snapshot_ids", []),
    }


def _build_resume_anchor_comparison(
    summary: dict[str, object],
) -> dict[str, object]:
    """Compare current and checkpoint identities from persisted resume diagnostics."""
    identity_maps = _resolve_resume_identity_maps(summary)
    if identity_maps is None:
        return dict(_EMPTY_RESUME_ANCHOR_COMPARISON)
    current_identity, checkpoint_identity = identity_maps
    matching_fields: list[object] = []
    mismatched_fields: list[object] = []
    missing_current_fields: list[object] = []
    missing_checkpoint_fields: list[object] = []
    for field in sorted(set(current_identity) | set(checkpoint_identity)):
        if field not in current_identity:
            missing_current_fields.append(field)
            continue
        if field not in checkpoint_identity:
            missing_checkpoint_fields.append(field)
            continue
        if current_identity[field] == checkpoint_identity[field]:
            matching_fields.append(field)
            continue
        mismatched_fields.append(field)
    return {
        "checkpoint_identity_present": True,
        "matching_fields": matching_fields,
        "mismatched_fields": mismatched_fields,
        "missing_current_fields": missing_current_fields,
        "missing_checkpoint_fields": missing_checkpoint_fields,
    }


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

    final_summary = _build_final_summary(
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
    final_summary["reproducibility_diagnostics"] = (
        _build_unified_reproducibility_diagnostics(final_summary)
    )
    return final_summary


__all__ = ["build_diagnostics_summary"]
