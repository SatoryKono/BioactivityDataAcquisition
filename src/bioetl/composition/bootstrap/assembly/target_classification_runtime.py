"""Resolve and assemble the target-classification runtime capability."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.application.core.wiring.registry import (
    TargetClassifiedTransformer,
    TargetTransformer,
)
from bioetl.application.core.wiring.transformer import BaseTransformer
from bioetl.application.composite.helpers.target_classification_stage import (
    CompositeTargetClassification,
)
from bioetl.application.services.target_runtime.scope import (
    get_target_classification_dependency,
)
from bioetl.composition.bootstrap.assembly.storage import (
    build_target_classification_session,
    hydrate_target_runtime_config,
    load_target_runtime_profile,
)
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    load_pipeline_config,
)
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
    if not exact_replay:
        config.target_classification.to_domain().require_active()
    return resolve_target_classification_profile(config).resolved_yaml_config


def validate_target_runtime_dependency(
    config: object, *, exact_replay: bool = False
) -> None:
    """Recheck pinned bytes immediately before a target run can clear outputs."""
    if (
        not isinstance(config, PipelineYamlConfig)
        or config.pipeline_name != "chembl_target"
    ):
        return
    if not exact_replay:
        config.target_classification.to_domain().require_active()
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
    if (
        target_profile.contract_version == "3.2.0"
        or target_profile.config.mode == "enrich"
    ):
        selected = TargetClassifiedTransformer.for_physical_contract(
            target_profile.contract_version
        )
    return (
        selected,
        target_profile.resolved_yaml_config,
        target_profile.contract_policy,
        target_profile.pandera_silver_schema,
        target_profile,
    )


def build_composite_target_classification_stage(
    config: object,
    *,
    settings: Settings | None = None,
) -> CompositeTargetClassification | None:
    """Wire post-join classification only for an enabled composite target."""
    if getattr(config, "name", None) != "composite_target":
        return None
    binding = get_target_classification_dependency()
    historical = (
        isinstance(binding, Mapping) and binding.get("replay_mode") == "historical"
    )
    pinned = binding.get("target_config") if isinstance(binding, Mapping) else None
    if historical and pinned is None:
        return None
    if isinstance(pinned, Mapping):
        yaml_config = resolve_target_classification_profile(
            hydrate_target_runtime_config(pinned)
        ).resolved_yaml_config
    else:
        yaml_config = resolve_target_runtime_config(
            load_pipeline_config("chembl_target")
        )
    if historical and yaml_config.target_classification.mode == "off":
        return None
    yaml_config.target_classification.to_domain().require_active()
    session = build_target_classification_session(
        yaml_config, settings or get_settings()
    )
    if session is None:
        raise ValueError("composite_target requires a target classification session")
    return CompositeTargetClassification(
        session,
        table_contract=yaml_config.target_classification.to_domain().contract_version,
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
