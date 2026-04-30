"""Pure helper utilities for run manifest inspection diff payloads."""

from __future__ import annotations

from typing import cast

from bioetl.domain.control_plane import RunManifest


def manifest_snapshot_ids(manifest: RunManifest) -> tuple[str, ...]:
    return tuple(
        sorted(
            snapshot.snapshot_id
            for source_ref in manifest.source_refs
            for snapshot in source_ref.input_snapshots
        )
    )


def planned_artifact_identity(manifest: RunManifest) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (artifact.layer, artifact.path) for artifact in manifest.planned_artifacts
        )
    )


def build_checkpoint_anchor_matches(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, bool]:
    return {
        "execution_fingerprint": (
            left_manifest.execution_fingerprint == right_manifest.execution_fingerprint
        ),
        "effective_config_hash": (
            left_manifest.code_provenance.effective_config_hash
            == right_manifest.code_provenance.effective_config_hash
        ),
        "effective_config_artifact_id": (
            left_manifest.code_provenance.effective_config_artifact_id
            == right_manifest.code_provenance.effective_config_artifact_id
        ),
        "contract_ref": (
            left_manifest.code_provenance.contract_ref
            == right_manifest.code_provenance.contract_ref
        ),
        "contract_version": (
            left_manifest.code_provenance.contract_version
            == right_manifest.code_provenance.contract_version
        ),
        "input_snapshot_ids": (
            manifest_snapshot_ids(left_manifest)
            == manifest_snapshot_ids(right_manifest)
        ),
    }


def build_manifest_diff_payload(
    *,
    classification: dict[str, object],
    semantic_equivalent: bool,
    occurrence_only: bool,
) -> dict[str, object]:
    return {
        "classification": classification["classification"],
        "semantic_equivalent": semantic_equivalent,
        "occurrence_only": occurrence_only,
        "semantic_difference_fields": list(
            cast(tuple[str, ...], classification["semantic_difference_fields"])
        ),
        "occurrence_difference_fields": list(
            cast(tuple[str, ...], classification["occurrence_difference_fields"])
        ),
        "noncanonical_difference_fields": list(
            cast(tuple[str, ...], classification["noncanonical_difference_fields"])
        ),
    }


def build_effective_config_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
    effective_config_match: bool,
) -> dict[str, object]:
    return {
        "semantic_equivalent": effective_config_match,
        "left_effective_config_hash": (
            left_manifest.code_provenance.effective_config_hash
        ),
        "right_effective_config_hash": (
            right_manifest.code_provenance.effective_config_hash
        ),
        "left_effective_config_artifact_id": (
            left_manifest.code_provenance.effective_config_artifact_id
        ),
        "right_effective_config_artifact_id": (
            right_manifest.code_provenance.effective_config_artifact_id
        ),
    }


def build_checkpoint_anchor_diff_payload(
    *,
    checkpoint_anchor_matches: dict[str, bool],
    checkpoint_compatible: bool,
) -> dict[str, object]:
    return {
        "compatible": checkpoint_compatible,
        "matching_fields": [
            name for name, matches in checkpoint_anchor_matches.items() if matches
        ],
        "mismatched_fields": [
            name for name, matches in checkpoint_anchor_matches.items() if not matches
        ],
    }


def build_lineage_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, object]:
    return {
        "planned_artifacts_match": (
            planned_artifact_identity(left_manifest)
            == planned_artifact_identity(right_manifest)
        ),
        "left_planned_artifact_count": len(left_manifest.planned_artifacts),
        "right_planned_artifact_count": len(right_manifest.planned_artifacts),
    }


def build_run_artifact_diff_payload(
    *,
    left_manifest: RunManifest,
    right_manifest: RunManifest,
) -> dict[str, object]:
    left_snapshots = manifest_snapshot_ids(left_manifest)
    right_snapshots = manifest_snapshot_ids(right_manifest)
    left_artifacts = planned_artifact_identity(left_manifest)
    right_artifacts = planned_artifact_identity(right_manifest)
    return {
        "input_snapshots_match": left_snapshots == right_snapshots,
        "left_input_snapshot_count": len(left_snapshots),
        "right_input_snapshot_count": len(right_snapshots),
        "planned_artifacts_match": left_artifacts == right_artifacts,
        "left_planned_artifact_count": len(left_artifacts),
        "right_planned_artifact_count": len(right_artifacts),
    }
