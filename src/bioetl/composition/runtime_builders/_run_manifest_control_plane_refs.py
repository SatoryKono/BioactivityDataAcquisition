"""Control-plane refs assembly for one persisted run manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders.run_manifest_support as _manifest_support
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest


def create_control_plane_refs_for_manifest(
    *,
    manifest: RunManifest,
    provenance: _manifest_support.RunManifestProvenanceBundle,
    contract_identity: _manifest_support.RunManifestContractIdentity,
    required_persistence_profile: str,
) -> _manifest_support.ManifestControlPlaneRefs:
    """Build canonical control-plane refs from one persisted manifest record."""
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        [
            snapshot
            for source_ref in getattr(manifest, "source_refs", ())
            for snapshot in getattr(source_ref, "input_snapshots", ())
        ]
    )
    return _manifest_support.create_control_plane_refs(
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        resolved_config_hash=provenance.resolved_config_hash,
        effective_config_hash=provenance.effective_config_hash,
        source_fingerprint=provenance.source_fingerprint,
        dq_contract_compatibility_hash=provenance.dq_contract_compatibility_hash,
        effective_config_artifact_id=provenance.effective_config_artifact_id,
        replay_parentage=(
            getattr(manifest, "replay_of_run_id", None),
            getattr(manifest, "replay_of_manifest_id", None),
        ),
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        contract=(
            contract_identity.contract_ref,
            contract_identity.contract_version,
            contract_identity.contract_schema_hash,
        ),
        policy=(
            contract_identity.dq_policy_ref,
            contract_identity.rule_bundle_version,
        ),
        normalization_profile=(
            contract_identity.normalization_profile_ref,
            contract_identity.normalization_profile_version,
            contract_identity.normalization_profile_hash,
        ),
        required_persistence_profile=required_persistence_profile,
    )
