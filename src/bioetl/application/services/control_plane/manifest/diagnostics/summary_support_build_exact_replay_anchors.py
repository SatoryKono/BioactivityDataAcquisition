"""Extracted build_exact_replay_anchors for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.control_plane import RunManifest


def build_exact_replay_anchors(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str] | frozenset[str],
    sorted_text_items: Callable[..., list[str]],
) -> dict[str, object]:
    """Return semantic replay anchors separately from occurrence diagnostics."""
    published_artifact_ids = sorted_text_items(
        [
            artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id")
            for artifact_ref in artifact_refs
        ]
    )
    published_artifact_paths = sorted_text_items(
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
        "normalization_profile_ref": summary.get("normalization_profile_ref"),
        "normalization_profile_version": summary.get("normalization_profile_version"),
        "normalization_profile_hash": summary.get("normalization_profile_hash"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_identity_fingerprint": summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "input_snapshot_ids": sorted_text_items(summary.get("input_snapshot_ids", [])),
        "input_snapshot_content_hashes": sorted_text_items(
            summary.get("input_snapshot_content_hashes", [])
        ),
        "published_artifact_ids": published_artifact_ids,
        "published_artifact_paths": published_artifact_paths,
        "lineage_fragment_ids": sorted(lineage_fragment_ids),
    }
    if summary.get("dependency_lock_hash") is not None:
        anchors["dependency_lock_hash"] = summary.get("dependency_lock_hash")
    return anchors
