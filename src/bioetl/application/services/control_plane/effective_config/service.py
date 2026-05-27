"""Application service for creating effective configuration artifacts."""

from __future__ import annotations

import json

from bioetl.application.services.control_plane.effective_config_context import (
    build_effective_config_context,
)
from bioetl.application.services.control_plane.effective_config_support import (
    build_effective_config_artifact_id,
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
from bioetl.domain.control_plane.reproducibility_policy import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
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
        normalization_profile_ref: str | None = None,
        normalization_profile_version: str | None = None,
        normalization_profile_hash: str | None = None,
    ) -> EffectiveConfigArtifact:
        """Create a reproducible effective-config artifact from resolved inputs."""
        validate_runtime_environment_provenance(
            runtime_overrides=runtime_overrides,
            required_persistence_profile=required_persistence_profile,
        )
        context = build_effective_config_context(
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
            source_refs=source_refs,
            dq_config=dq_config,
            resolution_policy=resolution_policy,
            required_persistence_profile=required_persistence_profile,
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
        )
        resolved_artifact_id = artifact_id or build_effective_config_artifact_id(
            context["semantic_identity_payload"]
        )
        return EffectiveConfigArtifact(
            artifact_id=resolved_artifact_id,
            pipeline_name=pipeline_name,
            pipeline_kind=pipeline_kind,
            source_refs=source_refs,
            source_class_provenance=context["source_class_provenance"],
            resolution_policy=context["resolved_policy"],
            resolved_config=context["resolved_snapshot"],
            runtime_overrides=context["overrides_snapshot"],
            execution_environment=context["execution_environment"],
            effective_execution_config=context["effective_snapshot"],
            resolved_config_hash=context["resolved_snapshot"].config_hash,
            effective_config_hash=context["effective_snapshot"].effective_hash,
            source_fingerprint=context["source_fingerprint"],
            contract_refs=context["contract_refs"],
            normalization_profile_ref=normalization_profile_ref,
            normalization_profile_version=normalization_profile_version,
            normalization_profile_hash=normalization_profile_hash,
            dq_policy_refs=context["dq_policy_refs"],
            dq_rule_bundle_versions=context["dq_rule_bundle_versions"],
            dq_contract_compatibility_hash=context["dq_contract_compatibility_hash"],
            dq_policy_snapshots=context["dq_policy_snapshots"],
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
