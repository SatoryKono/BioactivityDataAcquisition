"""Base run-manifest diagnostics helper aggregation seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.base_payload_sections import (
    _build_base_summary_core_payload,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base_replay_context import (
    _BaseSummaryReplayContext,
    _resolve_base_summary_replay_context,
)
from bioetl.domain.control_plane import RunManifest

EMPTY_RESUME_ANCHOR_COMPARISON = {
    "checkpoint_identity_present": False,
    "matching_fields": [],
    "mismatched_fields": [],
    "missing_current_fields": [],
    "missing_checkpoint_fields": [],
}


def _build_effective_config_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    return {
        "semantic": {
            "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
            "resolved_config_hash": summary.get("resolved_config_hash"),
            "effective_config_hash": summary.get("effective_config_hash"),
            "source_fingerprint": summary.get("source_fingerprint"),
        },
        "occurrence": {
            "run_id": summary.get("run_id"),
            "manifest_id": summary.get("manifest_id"),
            "manifest_created_at": summary.get("manifest_created_at"),
        },
        "diff_policy": {
            "semantic_anchor": "effective_config_hash",
            "occurrence_fields": ["run_id", "manifest_id", "manifest_created_at"],
            "config_hash_policy": "resolved_and_effective_hashes_only",
        },
    }


def resolve_resume_identity_maps(
    summary: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]] | None:
    """Return current/checkpoint identity maps when resume diagnostics contain both."""
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


def build_current_checkpoint_anchor_payload(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build the bounded current-manifest checkpoint-anchor projection."""
    return {
        "execution_fingerprint": summary.get("execution_fingerprint"),
        "manifest_id": summary.get("manifest_id"),
        "effective_config_hash": summary.get("effective_config_hash"),
        "contract_ref": summary.get("contract_ref"),
        "contract_version": summary.get("contract_version"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_ids": summary.get("input_snapshot_ids", []),
    }


def build_resume_anchor_comparison(
    summary: dict[str, object],
) -> dict[str, object]:
    """Compare current manifest identity against checkpoint resume identity."""
    identity_maps = resolve_resume_identity_maps(summary)
    if identity_maps is None:
        return dict(EMPTY_RESUME_ANCHOR_COMPARISON)
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


def build_checkpoint_anchor_projection(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build the bounded checkpoint-anchor diagnostics bundle."""
    return {
        "current_manifest_anchors": build_current_checkpoint_anchor_payload(summary),
        "resume_anchor_comparison": build_resume_anchor_comparison(summary),
    }


_build_checkpoint_anchor_projection = build_checkpoint_anchor_projection
_build_current_checkpoint_anchor_payload = build_current_checkpoint_anchor_payload
_build_resume_anchor_comparison = build_resume_anchor_comparison
_resolve_resume_identity_maps = resolve_resume_identity_maps


def _build_base_summary_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> dict[str, object]:
    """Build the base diagnostics payload before artifact defaults."""
    code_provenance = manifest.code_provenance
    summary = _build_base_summary_core_payload(
        manifest=manifest,
        replay_context=replay_context,
    )
    if code_provenance.dependency_lock_hash is not None:
        summary["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return summary


__all__ = [
    "EMPTY_RESUME_ANCHOR_COMPARISON",
    "_BaseSummaryReplayContext",
    "_build_base_summary_payload",
    "_build_checkpoint_anchor_projection",
    "_build_current_checkpoint_anchor_payload",
    "_build_effective_config_diagnostics",
    "_build_resume_anchor_comparison",
    "_resolve_base_summary_replay_context",
    "_resolve_resume_identity_maps",
    "build_checkpoint_anchor_projection",
    "build_current_checkpoint_anchor_payload",
    "build_resume_anchor_comparison",
    "resolve_resume_identity_maps",
]
