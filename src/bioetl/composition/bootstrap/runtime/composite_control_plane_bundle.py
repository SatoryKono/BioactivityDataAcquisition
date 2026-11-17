"""Control-plane artifact bundle for composite runtime bootstrap."""

from __future__ import annotations

from collections.abc import Mapping

from dataclasses import dataclass

from typing import TYPE_CHECKING

from bioetl.application.services.target_runtime.scope import (
    get_target_classification_dependency,
)

from bioetl.composition.bootstrap.assembly.storage import (
    build_target_classification_session,
    hydrate_target_runtime_config,
    load_target_runtime_profile,
    preflight_workflow_target_dependencies,
)

from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef

from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef

from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)

from bioetl.domain.ports import PipelineControlPlaneArtifacts as ControlPlaneArtifacts

from bioetl.infrastructure.config.contract_identity_resolution import (
    RunManifestContractIdentity,
)

from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
    target_v31_schema_hash,
)

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


@dataclass(frozen=True, slots=True)
class CompositeControlPlaneBundle(ControlPlaneArtifacts):
    """Optional control-plane artifacts materialized for one composite run."""

    run_ledger_service: RunLedgerService | None = None
    contract_ref: str | None = None
    contract_version: str | None = None


__all__ = [
    "CompositeControlPlaneBundle",
    "build_target_classification_session",
    "load_target_runtime_profile",
    "preflight_workflow_target_dependencies",
    "resolve_target_runtime_config",
    "target_classification_source_refs",
]


def resolve_target_runtime_config(config: PipelineYamlConfig) -> PipelineYamlConfig:
    """Choose one typed schema/hash profile, respecting a workflow's pinned input."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return config
    binding = get_target_classification_dependency()
    if binding is not None:
        payload = binding.get("target_config")
        if not isinstance(payload, Mapping):
            raise ValueError("workflow target dependency has no pinned configuration")
        config = hydrate_target_runtime_config(payload)
    return resolve_target_classification_profile(config).resolved_yaml_config


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


def validate_target_runtime_dependency(config: object) -> None:
    """Recheck pinned bytes immediately before a target run can clear outputs."""
    if not isinstance(config, PipelineYamlConfig):
        return
    profile = load_target_runtime_profile(config)
    stored = get_target_classification_dependency()
    if stored is None or profile is None:
        return
    if (
        stored.get("profile_sha256") != profile.profile_sha256
        or stored.get("snapshot_manifest_sha256")
        != profile.snapshot.snapshot_manifest_sha256
    ):
        raise ValueError("workflow target classification dependency identity changed")


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
