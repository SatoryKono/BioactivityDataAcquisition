"""Select and configure the target-classification transformer as one capability."""

from __future__ import annotations
from typing import TYPE_CHECKING
from bioetl.application.core.wiring.registry import (
    TargetClassifiedTransformer,
    TargetTransformer,
)
from bioetl.composition.bootstrap.assembly.storage import (
    build_target_classification_session,
)
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.config.target_classification_profile import (
    TargetClassificationSchemaProfile,
    resolve_target_classification_profile,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

if TYPE_CHECKING:
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.domain.ports import ContractPolicyProtocol
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.config.settings_api import Settings


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
