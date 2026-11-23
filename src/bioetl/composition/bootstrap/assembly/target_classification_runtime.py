"""Resolve and assemble the target-classification runtime capability."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.core.wiring.registry import (
    TargetClassifiedTransformer,
    TargetTransformer,
)
from bioetl.application.core.wiring.transformer import BaseTransformer
from bioetl.application.services.target_runtime.scope import (
    get_target_classification_dependency,
)
from bioetl.composition.bootstrap.assembly.storage import (
    build_target_classification_session,
    hydrate_target_runtime_config,
    load_target_runtime_profile,
)
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import ContractPolicyProtocol
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.config.target_classification_profile import (
    TargetClassificationSchemaProfile,
    resolve_target_classification_profile,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)


def resolve_target_runtime_config(
    config: PipelineYamlConfig, *, exact_replay: bool = False
) -> PipelineYamlConfig:
    """Choose one typed schema/hash profile, respecting a workflow's pinned input."""
    if not isinstance(config, PipelineYamlConfig) or (
        config.provider,
        config.entity_type,
    ) != ("chembl", "target"):
        return config
    binding = None if exact_replay else get_target_classification_dependency()
    if binding is not None:
        payload = binding.get("target_config")
        if not isinstance(payload, Mapping):
            raise ValueError("workflow target dependency has no pinned configuration")
        config = hydrate_target_runtime_config(payload)
    return resolve_target_classification_profile(config).resolved_yaml_config


def validate_target_runtime_dependency(
    config: object, *, exact_replay: bool = False
) -> None:
    """Recheck pinned bytes immediately before a target run can clear outputs."""
    if not isinstance(config, PipelineYamlConfig):
        return
    profile = load_target_runtime_profile(config)
    stored = None if exact_replay else get_target_classification_dependency()
    if stored is None or profile is None:
        return
    if (
        stored.get("profile_sha256") != profile.profile_sha256
        or stored.get("snapshot_manifest_sha256")
        != profile.snapshot.snapshot_manifest_sha256
    ):
        raise ValueError("workflow target classification dependency identity changed")


def select_target_transformer(
    pipeline_name: str,
    transformer_class: type[BaseTransformer],
    yaml_config: PipelineYamlConfig,
    contract_policy: ContractPolicyProtocol | None,
    pandera_silver_schema: object | None,
) -> tuple[
    type[BaseTransformer],
    PipelineYamlConfig,
    ContractPolicyProtocol | None,
    object | None,
    TargetClassificationSchemaProfile | None,
]:
    if pipeline_name != "chembl_target":
        return (
            transformer_class,
            yaml_config,
            contract_policy,
            pandera_silver_schema,
            None,
        )
    target_profile = resolve_target_classification_profile(
        yaml_config,
        contract_policy
        if isinstance(contract_policy, PipelineContractPolicy)
        else None,
    )
    selected = transformer_class
    if target_profile.config.mode == "enrich":
        selected = TargetClassifiedTransformer
    return (
        selected,
        target_profile.resolved_yaml_config,
        target_profile.contract_policy,
        target_profile.pandera_silver_schema,
        target_profile,
    )


def configure_target_transformer(
    transformer: BaseTransformer,
    yaml_config: PipelineYamlConfig,
    target_profile: TargetClassificationSchemaProfile | None,
    settings: Settings | None,
) -> None:
    """Bind the optional classification session after generic collaborators exist."""
    if target_profile is not None and target_profile.config.enabled:
        if not isinstance(transformer, TargetTransformer):
            raise TypeError("target classification requires a TargetTransformer")
        session = build_target_classification_session(
            yaml_config, settings or get_settings()
        )
        if session is not None:
            transformer.configure_target_classification(session)


def resolve_composite_post_join_classification_session(
    *,
    composite_name: str,
    settings: Settings | None = None,
    load_seed_config: object | None = None,
) -> object | None:
    """RF-003: bind chembl_target classification into composite_target merge host.

    Production mode stays ``off`` until a later RF admits enrich. When the seed
    entity config enables shadow/enrich, Composition injects the same session
    type used by the standalone transformer so post-join classification reuses
    compute/publish/finalize boundaries.
    """
    if composite_name != "composite_target":
        return None
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

    loader = load_seed_config or load_pipeline_config
    seed_config = loader("chembl_target")  # type: ignore[operator]
    if not isinstance(seed_config, PipelineYamlConfig):
        return None
    if not seed_config.target_classification.enabled:
        return None
    return build_target_classification_session(
        seed_config,
        settings or get_settings(),
        pipeline_name="composite_target",
    )
