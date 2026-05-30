"""Base-summary helper functions for run manifest diagnostics.

Extracted from _run_manifest_diagnostics_base.py to meet file size limits.
"""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


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


def _resolve_source_posture(
    policy_assessment: ReproducibilityPolicyAssessment,
) -> str:
    """Return whether manifested sources are snapshot-backed or live/unknown."""
    snapshot_envelope = policy_assessment.snapshot_envelope
    if snapshot_envelope.full_snapshot_envelope:
        return "immutable_snapshot_envelope"
    if snapshot_envelope.any_input_snapshots:
        return "partial_snapshot_envelope"
    return "live_or_unknown_inputs"


def _resolve_operator_replay_mode(
    *,
    replay_mode: str,
    continuation_mode: str,
    replay_readiness_verdict: str,
) -> str:
    """Return a compact CLI label for exact replay/resume/rebuild triage."""
    if replay_readiness_verdict == "exact_replay_blocked":
        return "Exact Replay Blocked"
    if replay_readiness_verdict == "lifecycle_projection_only":
        return "Lifecycle Projection"
    if replay_readiness_verdict == "incremental_new_run":
        return "Incremental New Run"
    if replay_readiness_verdict == "debug_only":
        return "Debug Only"
    if replay_mode == "exact_replay":
        return "Exact Replay"
    if replay_mode == "resume" or "resume" in continuation_mode:
        return "Resume"
    return "Rebuild"


def _build_code_provenance_state(manifest: RunManifest) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    blockers: list[str] = []
    if not code_provenance.git_commit:
        blockers.append("git_commit_missing")
    if str(code_provenance.source_revision_state or "").strip().lower() != "clean":
        blockers.append("source_revision_state_not_clean")
    if not code_provenance.dependency_lock_hash:
        blockers.append("dependency_lock_hash_missing")
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


def _build_planned_artifact_refs(manifest: RunManifest) -> list[dict[str, object]]:
    """Return planned artifact refs in the summary payload shape."""
    return [
        {"layer": artifact.layer, "path": artifact.path}
        for artifact in manifest.planned_artifacts
    ]


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "semantic": {
            "legacy_config_hash": summary.get("config_hash"),
            "legacy_config_hash_alias_of": "resolved_config_hash",
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "source_fingerprint": summary.get("source_fingerprint"),
            "config_hash_compatibility_anchor": summary.get("config_hash"),
            "config_hash_legacy_alias_of": "resolved_config_hash",
        },
        "occurrence": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
        },
        "diff_policy": {
            "semantic_anchor": "effective_config_hash",
            "occurrence_fields": ["run_id", "manifest_id", "manifest_created_at"],
            "config_hash_policy": ("deprecated_legacy_alias_for_resolved_config_hash"),
            "legacy_config_hash_display_only": True,
            "legacy_config_hash_replay_identity_anchor": False,
        },
    }


__all__ = [
    "_build_code_provenance_state",
    "_build_effective_config_diagnostics",
    "_build_planned_artifact_refs",
    "_resolve_operator_replay_mode",
    "_resolve_snapshot_status",
    "_resolve_source_posture",
]
