"""Helper functions for main diagnostics.

Extracted from manifest/diagnostics.py to meet file size limits.
"""

from __future__ import annotations

from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.base_effective_config_diagnostics import (
    _build_effective_config_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.checkpoint_projection import (
    build_checkpoint_anchor_projection as _build_checkpoint_anchor_projection,
)


def _build_unified_reproducibility_diagnostics_policy_payload(
    summary: dict[str, object],
    persistence_profile: dict[str, object],
) -> dict[str, object]:
    """Build policy section of unified reproducibility diagnostics."""
    return {
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
        "replay_control_plane_state": summary.get("replay_control_plane_state"),
        "replay_readiness_verdict": summary.get("replay_readiness_verdict"),
        "operator_replay_mode": summary.get("operator_replay_mode"),
        "replay_mode": summary.get("replay_mode"),
        "continuation_mode": summary.get("continuation_mode"),
        "replay_family_contract": summary.get("replay_family_contract"),
        "exact_replay_support_boundary": summary.get("exact_replay_support_boundary"),
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
    }


def _build_unified_reproducibility_diagnostics_semantic_identity(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build semantic identity section of unified reproducibility diagnostics."""
    return {
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
    }


def _build_unified_reproducibility_diagnostics_occurrence_identity(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build occurrence identity section of unified reproducibility diagnostics."""
    return {
        "run_id": summary.get("run_id"),
        "manifest_id": summary.get("manifest_id"),
        "manifest_created_at": summary.get("manifest_created_at"),
        "occurrence_only_diagnostics": summary.get(
            "occurrence_only_diagnostics",
            [],
        ),
    }


def _build_unified_reproducibility_diagnostics_checkpoint_anchors(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build checkpoint anchors section of unified reproducibility diagnostics."""
    return {
        "resume_contract": summary.get("resume_contract"),
        "resume_diagnostics": summary.get("resume_diagnostics"),
        **_build_checkpoint_anchor_projection(summary),
    }


def _build_unified_reproducibility_diagnostics_lineage(
    summary: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Build lineage section of unified reproducibility diagnostics."""
    return {
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "lineage_fragment_ids": summary.get("lineage_fragment_ids", []),
        "planned_artifact_count": summary.get("planned_artifact_count"),
        "published_artifact_count": summary.get("published_artifact_count"),
        "artifact_publication_closure": summary.get("artifact_publication_closure"),
        "produced_artifact_trace_complete": produced_artifact_trace.get("complete"),
    }


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
    policy_payload = _build_unified_reproducibility_diagnostics_policy_payload(
        summary=summary,
        persistence_profile=persistence_profile,
    )
    return {
        "policy": policy_payload,
        "semantic_identity": _build_unified_reproducibility_diagnostics_semantic_identity(
            summary
        ),
        "effective_config": _build_effective_config_diagnostics(summary),
        "occurrence_identity": _build_unified_reproducibility_diagnostics_occurrence_identity(
            summary
        ),
        "checkpoint_anchors": _build_unified_reproducibility_diagnostics_checkpoint_anchors(
            summary
        ),
        "lineage": _build_unified_reproducibility_diagnostics_lineage(
            summary, produced_artifact_trace
        ),
    }


__all__ = [
    "_build_unified_reproducibility_diagnostics",
]
