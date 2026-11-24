"""Target-classification identities shared by run and manifest assembly."""

from __future__ import annotations

from collections.abc import Callable
from typing import overload

from bioetl.composition.bootstrap.assembly.storage import (
    hydrate_target_runtime_config,
    load_target_runtime_profile,
)
from bioetl.composition.factories.pipeline.run_context_contract_identity import (
    NormalizedContractIdentity,
)
from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    resolve_target_runtime_config,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest, RunSourceRef
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.config.target_classification import resolve_physical_table_contract
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
    target_v32_normalization_profile,
)
from bioetl.infrastructure.config.contract_identity_resolution import (
    RunManifestContractIdentity,
)
from bioetl.infrastructure.config.pipeline_config_api import PipelineYamlConfig
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.config.target_classification_profile import (
    target_v31_schema_hash,
    target_v32_schema_hash,
)


def target_classification_contract_schema_identity(
    config: object,
) -> tuple[str, str] | None:
    """Return the actual enriched contract schema identity, preserving V30 otherwise."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return None
    classification = config.target_classification
    if classification.mode != "enrich":
        return None
    version = resolve_physical_table_contract(
        config.target_classification.mode,
        config.target_classification.table_contract,
    )
    if version == "3.2.0":
        return ("3.2.0", target_v32_schema_hash())
    return ("3.1.0", target_v31_schema_hash())


def target_classification_normalization_identity(
    config: object,
) -> tuple[str, str, str] | None:
    """Bind the selected additive normalization profile to execution metadata."""
    schema_identity = target_classification_contract_schema_identity(config)
    if schema_identity is None:
        return None
    version = target_classification_contract_schema_identity(config)
    profile = (
        target_v32_normalization_profile()
        if version is not None and version[0] == "3.2.0"
        else target_v31_normalization_profile()
    )
    identity = profile.identity
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


@overload
def restore_target_replay_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    current_config: PipelineYamlConfig,
    resolve_parent: Callable[..., RunManifest],
) -> PipelineYamlConfig: ...


@overload
def restore_target_replay_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    current_config: object,
    resolve_parent: Callable[..., RunManifest],
) -> object: ...


def restore_target_replay_config(
    *,
    ctx: PipelineRunContext,
    settings: Settings,
    current_config: object,
    resolve_parent: Callable[..., RunManifest],
) -> object:
    """Restore the saved target profile rather than consulting a newer default."""
    if ctx.pipeline_name != "chembl_target" or not bool(
        getattr(ctx, "exact_replay", False)
    ):
        return current_config

    if not isinstance(current_config, PipelineYamlConfig):
        return current_config
    has_parent = bool(
        getattr(ctx, "replay_of_manifest_id", None)
        or getattr(ctx, "replay_of_run_id", None)
    )
    if not has_parent and not current_config.target_classification.to_domain().enabled:
        return current_config
    parent = resolve_parent(ctx=ctx, settings=settings)
    if parent.pipeline_name != "chembl_target":
        raise ValueError("target replay parent pipeline mismatch")
    if not parent.resolved_config:
        raise ValueError("target replay parent has no pinned resolved configuration")

    return hydrate_target_runtime_config(parent.resolved_config)


def load_target_aware_pipeline_config(
    pipeline_name: str,
    load_pipeline_config_fn: Callable[[str], PipelineYamlConfig],
    validate_pk_contract_fn: Callable[[PipelineYamlConfig], None],
    ctx: PipelineRunContext | None = None,
    settings: Settings | None = None,
    resolve_parent: Callable[..., RunManifest] | None = None,
) -> PipelineYamlConfig:
    yaml_config = load_pipeline_config_fn(pipeline_name)
    if pipeline_name == "chembl_target":
        if ctx is not None and settings is not None:
            if resolve_parent is None:
                raise ValueError("target replay parent resolver is required")
            yaml_config = restore_target_replay_config(
                ctx=ctx,
                settings=settings,
                current_config=yaml_config,
                resolve_parent=resolve_parent,
            )
        yaml_config = resolve_target_runtime_config(
            yaml_config, exact_replay=bool(getattr(ctx, "exact_replay", False))
        )
    validate_pk_contract_fn(yaml_config)
    return yaml_config
