"""Payload section builders for base run-manifest diagnostics summaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.base_provenance_payloads import (
    _build_base_summary_code_provenance_payload,
    _build_code_provenance_state,
    _build_planned_artifact_refs,
)
from bioetl.domain.control_plane import RunManifest

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.base_replay_context import (
        _BaseSummaryReplayContext,
    )


def _is_exact_replay_eligible(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> bool:
    """Return whether manifest identity has enough anchors for exact replay."""
    del manifest
    return replay_context.exact_replay_eligible


def _build_base_summary_replay_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
    exact_replay_eligible: bool,
    replay_family_contract_payload: dict[str, object],
) -> dict[str, object]:
    """Build replay-related fields for base summary payload."""
    del exact_replay_eligible
    operator_replay_projection = replay_context.operator_replay_projection
    return {
        "replay_of_run_id": manifest.replay_of_run_id,
        "replay_of_manifest_id": manifest.replay_of_manifest_id,
        "replay_parentage": operator_replay_projection["replay_parentage"],
        "replay_capability": manifest.replay_capability.value,
        "replay_control_plane_state": replay_context.replay_control_plane_state,
        "required_persistence_profile": (
            replay_context.policy_assessment.required_persistence_profile
        ),
        "requested_exact_replay": replay_context.requested_exact_replay,
        "exact_replay_support_boundary": replay_context.exact_replay_support_boundary,
        "replay_capability_reason": replay_context.replay_capability_reason,
        **replay_family_contract_payload,
        **replay_context.replay_state_projection,
        "exact_replay_eligible": replay_context.exact_replay_eligible,
        "exact_replay_blockers": replay_context.exact_replay_blockers,
        "replay_readiness_verdict": replay_context.replay_readiness_verdict,
        "replay_resume_rebuild_verdict": replay_context.replay_resume_rebuild_verdict,
        "replay_next_action": replay_context.replay_next_action,
        "replay_mode": replay_context.replay_mode,
        "operator_replay_mode": operator_replay_projection["operator_replay_mode"],
        "continuation_mode": replay_context.continuation_mode,
        "replay_family_contract": replay_context.replay_family_contract,
        "replay_capability_assessment": replay_context.policy_assessment.to_dict(),
        "resume_contract": replay_context.resume_contract,
        "resume_diagnostics": None,
        "lineage_closure_boundary": operator_replay_projection[
            "lineage_closure_boundary"
        ],
    }


def _build_base_summary_snapshot_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
    exact_replay_eligible: bool,
) -> dict[str, object]:
    """Build snapshot-related fields for base summary payload."""
    del manifest, exact_replay_eligible
    return {
        "append_mode_semantic_sinks": replay_context.operator_replay_projection[
            "append_mode_semantic_sinks"
        ],
        "input_snapshot_ids": replay_context.input_snapshot_ids,
        "input_snapshot_content_hashes": replay_context.input_snapshot_content_hashes,
        "input_snapshot_identity_fingerprint": (
            replay_context.input_snapshot_identity_fingerprint
        ),
        "input_snapshot_count": len(replay_context.input_snapshots),
        "snapshot_status": replay_context.snapshot_status,
        "input_snapshots": replay_context.input_snapshots,
    }


def _build_base_summary_core_payload(
    *,
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    code_provenance_state = _build_code_provenance_state(manifest)
    dependency_lock_state = code_provenance_state["dependency_lock_state"]
    exact_replay_eligible = _is_exact_replay_eligible(manifest, replay_context)
    code_provenance_payload = _build_base_summary_code_provenance_payload(
        code_provenance=code_provenance,
        dependency_lock_state=dependency_lock_state,
        code_provenance_state=code_provenance_state,
    )
    replay_family_contract_payload = replay_context.replay_family_contract_payload
    replay_payload = _build_base_summary_replay_payload(
        manifest=manifest,
        replay_context=replay_context,
        exact_replay_eligible=exact_replay_eligible,
        replay_family_contract_payload=replay_family_contract_payload,
    )
    snapshot_payload = _build_base_summary_snapshot_payload(
        manifest=manifest,
        replay_context=replay_context,
        exact_replay_eligible=exact_replay_eligible,
    )
    return {
        "manifest_id": manifest.manifest_id,
        "manifest_created_at": manifest.created_at.isoformat(),
        "run_id": str(manifest.run_id),
        "pipeline_name": manifest.pipeline_name,
        "provider": manifest.provider,
        "entity": manifest.entity,
        "execution_fingerprint": manifest.execution_fingerprint,
        **code_provenance_payload,
        **replay_payload,
        "input_snapshot_missing_source_refs": list(
            replay_context.policy_assessment.snapshot_envelope.missing_snapshot_source_refs
        ),
        **snapshot_payload,
        "planned_artifacts": _build_planned_artifact_refs(manifest),
        "occurrence_only_diagnostics": [],
    }


__all__ = [
    "_build_base_summary_code_provenance_payload",
    "_build_base_summary_core_payload",
    "_build_base_summary_replay_payload",
    "_build_base_summary_snapshot_payload",
    "_is_exact_replay_eligible",
]
