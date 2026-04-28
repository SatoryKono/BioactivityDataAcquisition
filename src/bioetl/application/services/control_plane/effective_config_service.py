"""Application service for creating effective configuration artifacts."""

from __future__ import annotations

import json

from bioetl.application.services.control_plane._effective_config_support import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    SemanticIdentityPayloadContext,
    build_dq_components,
    build_effective_config_artifact_id,
    build_effective_execution_config,
    build_execution_environment_snapshot,
    build_resolved_config_snapshot,
    build_runtime_override_snapshot,
    build_semantic_identity_payload,
    build_source_class_provenance,
    compute_source_fingerprint,
    extract_contract_refs,
    resolve_resolution_policy,
    semantic_artifact_payload,
    serialize_artifact,
    validate_runtime_environment_provenance,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    EffectiveConfigArtifact,
    EffectiveConfigHashes,
)
from bioetl.domain.types import JsonDict


class EffectiveConfigService:
    """Create and compare effective configuration artifacts."""

    def create_effective_config_artifact(
        self,
        pipeline_name: str,
        pipeline_kind: str,
        resolved_config: JsonDict,
        runtime_overrides: JsonDict,
        source_refs: list[ConfigSourceRef],
        dq_config: DQConfig | None = None,
        resolution_policy: ConfigResolutionPolicy | None = None,
        artifact_id: str | None = None,
        required_persistence_profile: str = DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    ) -> EffectiveConfigArtifact:
        """Create a reproducible effective-config artifact from resolved inputs."""
        validate_runtime_environment_provenance(
            runtime_overrides=runtime_overrides,
            required_persistence_profile=required_persistence_profile,
        )
        resolved_policy = resolve_resolution_policy(resolution_policy)
        resolved_snapshot = build_resolved_config_snapshot(
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
        )
        overrides_snapshot = build_runtime_override_snapshot(runtime_overrides)
        execution_environment = build_execution_environment_snapshot(runtime_overrides)
        effective_snapshot = build_effective_execution_config(
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
        )

        dq_policy_refs, dq_policy_snapshots, dq_rule_bundle_versions = (
            build_dq_components(dq_config)
        )
        dq_contract_compatibility_hash = (
            "no_dq_policies"
            if not dq_policy_refs
            else ":".join(
                sorted(
                    ref.policy_hash
                    for ref in dq_policy_refs
                    if ref.policy_hash is not None and ref.policy_hash
                )
            )
            or "no_dq_policy_hashes"
        )
        resolved_source_fingerprint = compute_source_fingerprint(source_refs)
        resolved_contract_refs = extract_contract_refs(dq_config)
        source_class_provenance = build_source_class_provenance()
        semantic_identity_payload = build_semantic_identity_payload(
            request=SemanticIdentityPayloadContext(
                pipeline_name=pipeline_name,
                pipeline_kind=pipeline_kind,
                source_refs=source_refs,
                source_class_provenance=source_class_provenance,
                resolution_policy=resolved_policy,
                resolved_config=resolved_snapshot,
                runtime_overrides=overrides_snapshot,
                execution_environment=execution_environment,
                effective_execution_config=effective_snapshot,
                resolved_config_hash=resolved_snapshot.config_hash,
                effective_config_hash=effective_snapshot.effective_hash,
                source_fingerprint=resolved_source_fingerprint,
                contract_refs=resolved_contract_refs,
                dq_policy_refs=dq_policy_refs,
                dq_rule_bundle_versions=dq_rule_bundle_versions,
                dq_contract_compatibility_hash=dq_contract_compatibility_hash,
                dq_policy_snapshots=dq_policy_snapshots,
            ),
        )
        resolved_artifact_id = artifact_id or build_effective_config_artifact_id(
            semantic_identity_payload
        )
        return EffectiveConfigArtifact(
            artifact_id=resolved_artifact_id,
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            source_refs=source_refs,
            source_class_provenance=source_class_provenance,
            resolution_policy=resolved_policy,
            resolved_config=resolved_snapshot,
            runtime_overrides=overrides_snapshot,
            execution_environment=execution_environment,
            effective_execution_config=effective_snapshot,
            resolved_config_hash=resolved_snapshot.config_hash,
            effective_config_hash=effective_snapshot.effective_hash,
            source_fingerprint=resolved_source_fingerprint,
            contract_refs=resolved_contract_refs,
            dq_policy_refs=dq_policy_refs,
            dq_rule_bundle_versions=dq_rule_bundle_versions,
            dq_contract_compatibility_hash=dq_contract_compatibility_hash,
            dq_policy_snapshots=dq_policy_snapshots,
        )

    def serialize_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize one persisted artifact envelope with semantic + occurrence data."""
        return serialize_artifact(artifact)

    def serialize_semantic_artifact(self, artifact: EffectiveConfigArtifact) -> str:
        """Serialize only the semantic effective-config payload deterministically."""
        return json.dumps(
            semantic_artifact_payload(artifact),
            sort_keys=True,
            separators=(",", ":"),
        )

    def compute_artifact_hashes(
        self, artifact: EffectiveConfigArtifact
    ) -> EffectiveConfigHashes:
        """Extract the canonical hash bundle from an effective-config artifact."""
        return EffectiveConfigHashes(
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            source_fingerprint=artifact.source_fingerprint,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )

    def check_dq_compatibility(
        self,
        artifact1: EffectiveConfigArtifact,
        artifact2: EffectiveConfigArtifact,
    ) -> bool:
        """Compare artifacts by their DQ compatibility hash."""
        return bool(
            artifact1.dq_contract_compatibility_hash
            == artifact2.dq_contract_compatibility_hash
        )

    def create_artifact_from_pipeline_config(
        self,
        pipeline_name: str,
        pipeline_kind: str,
        pipeline_config: JsonDict,
        dq_config: DQConfig | None = None,
        runtime_overrides: JsonDict | None = None,
        source_refs: list[ConfigSourceRef] | None = None,
    ) -> EffectiveConfigArtifact:
        """Create an artifact directly from pipeline config and optional overrides."""
        if runtime_overrides is None:
            runtime_overrides = {}
        if source_refs is None:
            source_refs = []
        return self.create_effective_config_artifact(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=pipeline_config,
            runtime_overrides=runtime_overrides,
            source_refs=source_refs,
            dq_config=dq_config,
        )


def create_effective_config_service() -> EffectiveConfigService:
    """Factory for the effective configuration service."""
    return EffectiveConfigService()
