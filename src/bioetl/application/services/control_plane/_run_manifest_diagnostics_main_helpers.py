"""Helper functions for main diagnostics.

Extracted from run_manifest_diagnostics.py to meet file size limits.
"""

from __future__ import annotations

from typing import cast

from bioetl.application.services.control_plane._run_manifest_diagnostics_base import (
    _build_effective_config_diagnostics,
)


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
            "replay_readiness_verdict": summary.get("replay_readiness_verdict"),
            "operator_replay_mode": summary.get("operator_replay_mode"),
            "replay_mode": summary.get("replay_mode"),
            "continuation_mode": summary.get("continuation_mode"),
            "replay_family_contract": summary.get("replay_family_contract"),
            "exact_replay_support_boundary": summary.get(
                "exact_replay_support_boundary"
            ),
            "post_capture_replayable_parent_supported": summary.get(
                "post_capture_replayable_parent_supported"
            ),
            "post_capture_replayable_parent_boundary": summary.get(
                "post_capture_replayable_parent_boundary"
            ),
            "historical_live_run_upgrade_policy": summary.get(
                "historical_live_run_upgrade_policy"
            ),
            "historical_live_run_upgrade_boundary": summary.get(
                "historical_live_run_upgrade_boundary"
            ),
            "historical_live_run_upgrade_reason": summary.get(
                "historical_live_run_upgrade_reason"
            ),
            "broader_historical_exact_replay_policy": summary.get(
                "broader_historical_exact_replay_policy"
            ),
            "broader_historical_exact_replay_boundary": summary.get(
                "broader_historical_exact_replay_boundary"
            ),
            "broader_historical_exact_replay_reason": summary.get(
                "broader_historical_exact_replay_reason"
            ),
            "broader_historical_exact_replay_state": summary.get(
                "broader_historical_exact_replay_state"
            ),
            "historical_live_run_upgrade_state": summary.get(
                "historical_live_run_upgrade_state"
            ),
            "replay_occurrence_kind": summary.get("replay_occurrence_kind"),
            "exact_replay_blockers": summary.get("exact_replay_blockers", []),
            "capability_assessment": summary.get(
                "replay_capability_assessment",
                {},
            ),
        },
        "semantic_identity": {
            "execution_fingerprint": summary.get("execution_fingerprint"),
            "legacy_config_hash": summary.get("config_hash"),
            "legacy_config_hash_alias_of": "resolved_config_hash",
            "legacy_config_hash_replay_identity_anchor": False,
            "config_hash_compatibility_anchor": summary.get("config_hash"),
            "config_hash_legacy_alias_of": "resolved_config_hash",
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "input_snapshot_identity_fingerprint": summary.get(
                "input_snapshot_identity_fingerprint"
            ),
            "snapshot_status": summary.get("snapshot_status"),
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
    from bioetl.application.services.control_plane._run_manifest_diagnostics_base import (
        _EMPTY_RESUME_ANCHOR_COMPARISON,
        _resolve_resume_identity_maps,
    )

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
    "_build_current_checkpoint_anchor_payload",
    "_build_resume_anchor_comparison",
    "_build_unified_reproducibility_diagnostics",
]
