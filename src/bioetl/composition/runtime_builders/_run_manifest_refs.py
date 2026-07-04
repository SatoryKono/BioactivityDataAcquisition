"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    DataRootMode as DataRootMode,
    build_planned_artifacts as build_planned_artifacts,
    control_plane_root as control_plane_root,
    is_explicit_data_root_configured as is_explicit_data_root_configured,
    resolve_data_root_mode as resolve_data_root_mode,
)
from bioetl.composition.runtime_builders._run_manifest_identity_ref_values import (
    build_control_plane_identity_ref_values,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    build_contract_identity_field_values_from_mapping,
)


@dataclass(frozen=True, slots=True)
class ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    execution_fingerprint: str | None
    config_hash: str | None
    resolved_config_hash: str | None
    effective_config_hash: str | None
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    replay_of_run_id: str | None = None
    replay_of_manifest_id: str | None = None
    input_snapshot_fingerprint: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    contract_schema_hash: str | None = None
    dq_policy_ref: str | None = None
    rule_bundle_version: str | None = None
    normalization_profile_ref: str | None = None
    normalization_profile_version: str | None = None
    normalization_profile_hash: str | None = None
    required_persistence_profile: str | None = None

def create_control_plane_refs(
    manifest_id: str,
    execution_fingerprint: str,
    resolved_config_hash: str,
    effective_config_hash: str,
    source_fingerprint: str | None,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    replay_of_run_id: str | None,
    replay_of_manifest_id: str | None,
    input_snapshot_fingerprint: str | None,
    contract_ref: str,
    contract_version: str | None,
    contract_schema_hash: str | None,
    dq_policy_ref: str | None,
    rule_bundle_version: str | None,
    normalization_profile_ref: str | None,
    normalization_profile_version: str | None,
    normalization_profile_hash: str | None,
    required_persistence_profile: str | None,
) -> ManifestControlPlaneRefs:
    """Build the compact control-plane refs bundle returned to callers."""
    contract_identity_values = build_contract_identity_field_values_from_mapping(
        locals()
    )
    return ManifestControlPlaneRefs(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        config_hash=resolved_config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        **build_control_plane_identity_ref_values(
            contract_identity_values=contract_identity_values,
            required_persistence_profile=required_persistence_profile,
        ),
    )
