"""Pure helper utilities for run manifest inspection diff payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from bioetl.application.services.control_plane._run_manifest_inspection_artifact_refs import (
    build_artifact_ref_semantic_diff,
)
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
        "normalization_profile_ref": (
            left_manifest.code_provenance.normalization_profile_ref
            == right_manifest.code_provenance.normalization_profile_ref
        ),
        "normalization_profile_version": (
            left_manifest.code_provenance.normalization_profile_version
            == right_manifest.code_provenance.normalization_profile_version
        ),
        "normalization_profile_hash": (
            left_manifest.code_provenance.normalization_profile_hash
            == right_manifest.code_provenance.normalization_profile_hash
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
    left_artifact_refs: tuple[Mapping[str, object], ...] = (),
    right_artifact_refs: tuple[Mapping[str, object], ...] = (),
) -> dict[str, object]:
    left_snapshots = manifest_snapshot_ids(left_manifest)
    right_snapshots = manifest_snapshot_ids(right_manifest)
    left_artifacts = planned_artifact_identity(left_manifest)
    right_artifacts = planned_artifact_identity(right_manifest)
    payload = {
        "input_snapshots_match": left_snapshots == right_snapshots,
        "left_input_snapshot_count": len(left_snapshots),
        "right_input_snapshot_count": len(right_snapshots),
        "planned_artifacts_match": left_artifacts == right_artifacts,
        "left_planned_artifact_count": len(left_artifacts),
        "right_planned_artifact_count": len(right_artifacts),
    }
    if left_artifact_refs or right_artifact_refs:
        payload.update(
            build_artifact_ref_semantic_diff(
                left_artifact_refs=left_artifact_refs,
                right_artifact_refs=right_artifact_refs,
            )
        )
    return payload


def build_authoritative_replay_dossier(
    *,
    manifest: RunManifest,
    diagnostics: dict[str, object],
    identity_graph: dict[str, object],
) -> dict[str, object]:
    """Build one compact operator-facing summary of the authoritative replay dossier."""
    code_provenance = manifest.code_provenance
    artifact_refs = diagnostics.get("artifact_refs")
    lineage_fragment_ids = diagnostics.get("lineage_fragment_ids")
    input_snapshot_ids = diagnostics.get("input_snapshot_ids")
    input_snapshot_hashes = diagnostics.get("input_snapshot_content_hashes")
    if not isinstance(artifact_refs, list):
        artifact_refs = []
    if not isinstance(lineage_fragment_ids, list):
        lineage_fragment_ids = []
    if not isinstance(input_snapshot_ids, list):
        input_snapshot_ids = []
    if not isinstance(input_snapshot_hashes, list):
        input_snapshot_hashes = []
    published_artifact_refs = [
        {
            key: value
            for key, value in artifact_ref.items()
            if key
            in {
                "stage",
                "dataset_ref",
                "artifact_id",
                "lineage_fragment_id",
                "artifact_path",
                "metadata_path",
                "run_id",
                "manifest_id",
            }
        }
        for artifact_ref in artifact_refs
        if isinstance(artifact_ref, Mapping)
    ]
    checkpoint_identity = {
        key: value
        for key, value in {
            "required_persistence_profile": diagnostics.get(
                "required_persistence_profile"
            ),
            "execution_fingerprint": manifest.execution_fingerprint,
            "effective_config_hash": code_provenance.effective_config_hash,
            "effective_config_artifact_id": (
                code_provenance.effective_config_artifact_id
            ),
            "contract_ref": code_provenance.contract_ref,
            "contract_version": code_provenance.contract_version,
            "normalization_profile_ref": code_provenance.normalization_profile_ref,
            "normalization_profile_version": (
                code_provenance.normalization_profile_version
            ),
            "normalization_profile_hash": code_provenance.normalization_profile_hash,
            "input_snapshot_identity_fingerprint": diagnostics.get(
                "input_snapshot_identity_fingerprint"
            ),
            "input_snapshot_ids": input_snapshot_ids,
        }.items()
        if value not in (None, [], "")
    }
    return {
        "truth_boundary": "authoritative_replay_artifacts_only",
        "authoritative_replay_artifacts": [
            "run_manifest",
            "effective_config_artifact",
            "lineage_fragment",
            "layer_metadata",
            "checkpoint_metadata",
            "input_snapshot_envelope",
        ],
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "execution_fingerprint": manifest.execution_fingerprint,
        "git_commit": code_provenance.git_commit,
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
        "effective_config_hash": code_provenance.effective_config_hash,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "required_persistence_profile": diagnostics.get(
            "required_persistence_profile"
        ),
        "exact_replay_support_boundary": diagnostics.get(
            "exact_replay_support_boundary"
        ),
        "snapshot_status": diagnostics.get("snapshot_status"),
        "input_snapshot_ids": input_snapshot_ids,
        "input_snapshot_content_hashes": input_snapshot_hashes,
        "input_snapshot_identity_fingerprint": diagnostics.get(
            "input_snapshot_identity_fingerprint"
        ),
        "lineage_fragment_ids": [
            value for value in lineage_fragment_ids if isinstance(value, str)
        ],
        "published_artifact_refs": published_artifact_refs,
        "planned_artifact_count": diagnostics.get("planned_artifact_count"),
        "published_artifact_count": diagnostics.get("published_artifact_count"),
        "identity_graph_complete": diagnostics.get("identity_graph_complete"),
        "checkpoint_identity": checkpoint_identity,
        "canonical_execution_identity": identity_graph.get(
            "canonical_execution_identity", {}
        ),
    }
