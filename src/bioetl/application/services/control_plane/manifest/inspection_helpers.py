"""Pure helper utilities for run manifest inspection diff payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_contract_identity_anchor_fields,
)
from bioetl.application.services.control_plane.manifest.inspection_artifact_refs import (
    build_artifact_ref_semantic_diff,
)
from bioetl.domain.control_plane import RunManifest

_AUTHORITATIVE_REPLAY_ARTIFACTS = [
    "run_manifest",
    "effective_config_artifact",
    "lineage_fragment",
    "layer_metadata",
    "checkpoint_metadata",
    "input_snapshot_envelope",
]
_PUBLISHED_ARTIFACT_REF_KEYS = {
    "stage",
    "dataset_ref",
    "artifact_id",
    "lineage_fragment_id",
    "artifact_path",
    "metadata_path",
    "run_id",
    "manifest_id",
}


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
    payload: dict[str, object] = {
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


def _list_payload_values(
    diagnostics: Mapping[str, object],
    key: str,
) -> list[object]:
    value = diagnostics.get(key)
    return value if isinstance(value, list) else []


def _published_artifact_dossier_refs(
    artifact_refs: list[object],
) -> list[dict[str, object]]:
    return [
        {
            key: value
            for key, value in artifact_ref.items()
            if key in _PUBLISHED_ARTIFACT_REF_KEYS
        }
        for artifact_ref in artifact_refs
        if isinstance(artifact_ref, Mapping)
    ]


def _checkpoint_identity_payload(
    *,
    manifest: RunManifest,
    diagnostics: Mapping[str, object],
    input_snapshot_ids: list[object],
) -> dict[str, object]:
    code_provenance = manifest.code_provenance
    checkpoint_identity = {
        "required_persistence_profile": diagnostics.get("required_persistence_profile"),
        "execution_fingerprint": manifest.execution_fingerprint,
        **build_contract_identity_anchor_fields(
            code_provenance,
            include_effective_config_hash=True,
        ),
        "input_snapshot_identity_fingerprint": diagnostics.get(
            "input_snapshot_identity_fingerprint"
        ),
        "input_snapshot_ids": input_snapshot_ids,
    }
    return {
        key: value
        for key, value in checkpoint_identity.items()
        if value not in (None, [], "")
    }


def build_authoritative_replay_dossier(
    *,
    manifest: RunManifest,
    diagnostics: dict[str, object],
    identity_graph: dict[str, object],
) -> dict[str, object]:
    """Build one compact operator-facing summary of the authoritative replay dossier."""
    code_provenance = manifest.code_provenance
    artifact_refs = _list_payload_values(diagnostics, "artifact_refs")
    lineage_fragment_ids = _list_payload_values(diagnostics, "lineage_fragment_ids")
    input_snapshot_ids = _list_payload_values(diagnostics, "input_snapshot_ids")
    input_snapshot_hashes = _list_payload_values(
        diagnostics, "input_snapshot_content_hashes"
    )
    return {
        "truth_boundary": "authoritative_replay_artifacts_only",
        "authoritative_replay_artifacts": _AUTHORITATIVE_REPLAY_ARTIFACTS,
        "manifest_id": manifest.manifest_id,
        "run_id": str(manifest.run_id),
        "execution_fingerprint": manifest.execution_fingerprint,
        "git_commit": code_provenance.git_commit,
        "effective_config_artifact_id": code_provenance.effective_config_artifact_id,
        "effective_config_hash": code_provenance.effective_config_hash,
        "contract_ref": code_provenance.contract_ref,
        "contract_version": code_provenance.contract_version,
        "required_persistence_profile": diagnostics.get("required_persistence_profile"),
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
        "published_artifact_refs": _published_artifact_dossier_refs(artifact_refs),
        "planned_artifact_count": diagnostics.get("planned_artifact_count"),
        "published_artifact_count": diagnostics.get("published_artifact_count"),
        "identity_graph_complete": diagnostics.get("identity_graph_complete"),
        "checkpoint_identity": _checkpoint_identity_payload(
            manifest=manifest,
            diagnostics=diagnostics,
            input_snapshot_ids=input_snapshot_ids,
        ),
        "canonical_execution_identity": identity_graph.get(
            "canonical_execution_identity", {}
        ),
    }
