"""Target-classification identities shared by run and manifest assembly."""

from __future__ import annotations
from bioetl.composition.bootstrap.assembly.storage import load_target_runtime_profile
from bioetl.composition.factories.pipeline.run_context_contract_identity import (
    NormalizedContractIdentity,
)
from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.config.contract_identity_resolution import (
    RunManifestContractIdentity,
)
from bioetl.infrastructure.config.target_classification_profile import (
    target_v31_schema_hash,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def target_classification_contract_schema_identity(
    config: object,
) -> tuple[str, str] | None:
    """Return the actual enriched contract schema identity, preserving V30 otherwise."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return None
    if config.target_classification.mode != "enrich":
        return None

    return ("3.1.0", target_v31_schema_hash())


def target_classification_normalization_identity(
    config: object,
) -> tuple[str, str, str] | None:
    """Bind the actual additive V31 normalization profile to execution metadata."""
    if target_classification_contract_schema_identity(config) is None:
        return None

    identity = target_v31_normalization_profile().identity
    return identity.profile_name, identity.profile_version, identity.profile_hash


def apply_target_contract_identity(
    config: object, identity: RunManifestContractIdentity
) -> RunManifestContractIdentity:
    """Apply only the selected V31 schema/normalization anchors, preserving DQ."""
    schema_identity = target_classification_contract_schema_identity(config)
    if schema_identity is None:
        return identity
    normalization = target_classification_normalization_identity(config)
    assert normalization is not None
    return RunManifestContractIdentity(
        contract_ref=identity.contract_ref,
        dq_policy_ref=identity.dq_policy_ref,
        rule_bundle_version=identity.rule_bundle_version,
        contract_version=schema_identity[0],
        contract_schema_hash=schema_identity[1],
        normalization_profile_ref=normalization[0],
        normalization_profile_version=normalization[1],
        normalization_profile_hash=normalization[2],
    )


def target_classification_source_refs(
    config: object,
) -> tuple[RunSourceRef, ...]:
    if not isinstance(config, PipelineYamlConfig):
        return ()
    profile = load_target_runtime_profile(config)
    if profile is None:
        return ()
    return (
        RunSourceRef(
            provider="iuphar",
            entity="target_classification",
            pipeline_name="chembl_target",
            input_snapshots=(
                RunInputSnapshotRef(
                    snapshot_id=profile.snapshot.snapshot.snapshot_id,
                    content_hash=profile.snapshot.snapshot_manifest_sha256,
                    immutable_uri=profile.snapshot.immutable_uri,
                ),
                RunInputSnapshotRef(
                    snapshot_id="profile:" + profile.profile_sha256,
                    content_hash=profile.profile_sha256,
                    immutable_uri=profile.profile_uri,
                ),
            ),
        ),
    )


def target_classification_config_source_refs(config: object) -> list[ConfigSourceRef]:
    """Anchor immutable dependency bytes in effective-config source identity."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return []
    return [
        ConfigSourceRef(
            source_type="file",
            source_path=snapshot.immutable_uri,
            source_hash=snapshot.content_hash,
            raw_source_hash=snapshot.content_hash,
            source_hash_strategy="raw_bytes",
            source_hash_version="sha256-v1",
            raw_source_hash_version="sha256-v1",
            priority=100,
        )
        for source in target_classification_source_refs(config)
        for snapshot in source.input_snapshots
        if snapshot.immutable_uri is not None
    ]


def target_run_context_identity(
    pipeline_name: str,
    yaml_config: PipelineYamlConfig,
    contract_identity: NormalizedContractIdentity,
) -> NormalizedContractIdentity:
    """Apply the target schema and normalization identities together."""
    if pipeline_name != "chembl_target":
        return contract_identity
    target_identity = target_classification_contract_schema_identity(yaml_config)
    if target_identity is None:
        return contract_identity
    normalization = target_classification_normalization_identity(yaml_config)
    assert normalization is not None
    return (
        contract_identity[0],
        *target_identity,
        *contract_identity[3:5],
        *normalization,
    )
