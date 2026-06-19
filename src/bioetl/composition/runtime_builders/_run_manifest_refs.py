"""Control-plane ref helpers for manifest builders."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    DataRootMode as DataRootMode,
    build_planned_artifacts as build_planned_artifacts,
    control_plane_root as control_plane_root,
    is_explicit_data_root_configured as is_explicit_data_root_configured,
    resolve_data_root_mode as resolve_data_root_mode,
)
from bioetl.composition.runtime_builders._run_manifest_context_support import (
    RunManifestProvenanceBundle as RunManifestProvenanceBundle,
    apply_manifest_updates_to_mutable_context as apply_manifest_updates_to_mutable_context,
    build_dataclass_manifest_updates as build_dataclass_manifest_updates,
    build_run_manifest_provenance_bundle as build_run_manifest_provenance_bundle,
    extract_optional_updates_from_refs as extract_optional_updates_from_refs,
    iter_optional_control_plane_updates as iter_optional_control_plane_updates,
    iter_optional_control_plane_updates_from_mapping as iter_optional_control_plane_updates_from_mapping,
    resolve_run_context_values as resolve_run_context_values,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext


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
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        normalization_profile_ref=normalization_profile_ref,
        normalization_profile_version=normalization_profile_version,
        normalization_profile_hash=normalization_profile_hash,
        required_persistence_profile=required_persistence_profile,
    )
