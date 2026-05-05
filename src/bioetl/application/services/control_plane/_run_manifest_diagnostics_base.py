"""Base-summary helpers for run manifest diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane._run_manifest_diagnostics_persistence import (
    build_lineage_closure_boundary,
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
    _resolve_continuation_mode,
    _resolve_exact_replay_blockers,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_capability_reason,
    _resolve_replay_family_contract,
    _resolve_replay_mode,
)
from bioetl.application.services.control_plane._run_manifest_diagnostics_summary import (
    _build_exact_replay_anchors,
    _build_produced_artifact_trace,
)
from bioetl.domain.control_plane import RunManifest
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
    continuation_mode: str
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
        continuation_mode=_resolve_continuation_mode(
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


def _build_code_provenance_state(manifest: RunManifest) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    blockers: list[str] = []
    if not code_provenance.git_commit:
        blockers.append("git_commit_missing")
    if str(code_provenance.source_revision_state or "").strip().lower() != "clean":
        blockers.append("source_revision_state_not_clean")
    state: dict[str, object] = {
        "git_commit": code_provenance.git_commit,
        "source_revision_state": code_provenance.source_revision_state,
        "dependency_lock_state": (
            "present" if code_provenance.dependency_lock_hash is not None else "missing"
        ),
        "strict_code_provenance_ready": not blockers,
        "strict_code_provenance_blockers": blockers,
    }
    if code_provenance.dependency_lock_hash is not None:
        state["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return state


def _resolve_snapshot_status(
    *,
    input_snapshots: list[dict[str, object]],
    exact_replay_eligible: bool,
    replay_mode: str,
) -> str:
    """Return operator-facing completeness of immutable input snapshots."""
    if not input_snapshots:
        return "none"
    if exact_replay_eligible or replay_mode in {
        "exact_replay",
        "same_data_state_recovery",
    }:
        return "full"
    return "partial"


def _resolve_operator_replay_mode(
    *,
    replay_mode: str,
    continuation_mode: str,
) -> str:
    """Return a compact CLI label for exact replay/resume/rebuild triage."""
    if replay_mode == "exact_replay":
        return "Exact Replay"
    if replay_mode == "resume" or "resume" in continuation_mode:
        return "Resume"
    return "Rebuild"


def _build_base_summary_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    code_provenance_state = _build_code_provenance_state(manifest)
    dependency_lock_state = code_provenance_state["dependency_lock_state"]
    exact_replay_eligible = (
        manifest.replay_capability.value == "exact_replay_supported"
        and not replay_context.exact_replay_blockers
    )
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
        "dependency_lock_state": dependency_lock_state,
        "code_provenance_state": code_provenance_state,
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
        "exact_replay_eligible": exact_replay_eligible,
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
        "operator_replay_mode": _resolve_operator_replay_mode(
            replay_mode=replay_context.replay_mode,
            continuation_mode=replay_context.continuation_mode,
        ),
        "continuation_mode": replay_context.continuation_mode,
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
        "snapshot_status": _resolve_snapshot_status(
            input_snapshots=replay_context.input_snapshots,
            exact_replay_eligible=exact_replay_eligible,
            replay_mode=replay_context.replay_mode,
        ),
        "input_snapshots": replay_context.input_snapshots,
        "planned_artifacts": [
            {"layer": artifact.layer, "path": artifact.path}
            for artifact in manifest.planned_artifacts
        ],
        "occurrence_only_diagnostics": [],
    }
    if code_provenance.dependency_lock_hash is not None:
        summary["dependency_lock_hash"] = code_provenance.dependency_lock_hash
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


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
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
            "occurrence_fields": ["run_id", "manifest_id", "manifest_created_at"],
            "config_hash_policy": "legacy_alias_for_resolved_config_hash",
        },
    }


def _build_current_checkpoint_anchor_payload(
    summary: dict[str, object],
) -> dict[str, object]:
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
        elif field not in checkpoint_identity:
            missing_checkpoint_fields.append(field)
        elif current_identity[field] == checkpoint_identity[field]:
            matching_fields.append(field)
        else:
            mismatched_fields.append(field)
    return {
        "checkpoint_identity_present": True,
        "matching_fields": matching_fields,
        "mismatched_fields": mismatched_fields,
        "missing_current_fields": missing_current_fields,
        "missing_checkpoint_fields": missing_checkpoint_fields,
    }


__all__ = [
    "_BaseSummaryReplayContext",
    "_build_base_summary_payload",
    "_build_current_checkpoint_anchor_payload",
    "_build_effective_config_diagnostics",
    "_build_resume_anchor_comparison",
    "_resolve_base_summary_replay_context",
    "_resolve_resume_identity_maps",
]
