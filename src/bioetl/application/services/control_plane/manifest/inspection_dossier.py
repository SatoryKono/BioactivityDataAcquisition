"""Authoritative replay dossier builders for run-manifest inspection."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.services.control_plane.manifest.execution_identity_support import (
    build_contract_identity_anchor_fields,
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


__all__ = ["build_authoritative_replay_dossier"]
