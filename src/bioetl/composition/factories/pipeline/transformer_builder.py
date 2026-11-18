"""Transformer-construction helpers for pipeline factory wiring."""

from __future__ import annotations


from bioetl.composition.services.target_classification_transformer import (
    select_target_transformer,
    configure_target_transformer,
)
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.transformer import build_structural_policy
from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies,
    publication_vocabulary_kwargs,
)
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)

if TYPE_CHECKING:
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.ports import ContractPolicyProtocol, MetricsPort, TracingPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.config.settings_api import Settings


@dataclass(frozen=True, slots=True)
class TransformerBuilder:
    provider: str
    pipeline_name: str
    entity_type_extractor: Callable[[str], str | None]
    contract_policy_loader: Callable[
        [str, str],
        ContractPolicyProtocol,
    ] = load_pipeline_contract_policy

    def build(
        self,
        *,
        transformer_class: type[BaseTransformer] | None,
        yaml_config: PipelineYamlConfig,
        domain_config: PipelineConfig,
        pandera_silver_schema: object | None,
        tracer: TracingPort | None,
        metrics: MetricsPort | None,
        settings: Settings | None = None,
    ) -> BaseTransformer | None:
        """Build transformer instance or return ``None`` when class is absent."""
        if transformer_class is None:
            return None

        entity_type = self.entity_type_extractor(self.pipeline_name)
        contract_policy = self._load_contract_policy(entity_type)
        (
            transformer_class,
            yaml_config,
            contract_policy,
            pandera_silver_schema,
            target_profile,
        ) = select_target_transformer(
            self.pipeline_name,
            transformer_class,
            yaml_config,
            contract_policy,
            pandera_silver_schema,
        )

        authoritative_hash_policy = yaml_config.content_hash_policy
        identity_service = EntityIdentityGenerator(
            content_hash_include_fields=(
                set(authoritative_hash_policy.include_fields)
                if authoritative_hash_policy is not None
                else (set(yaml_config.content_hash.include) or None)
            ),
            content_hash_exclude_fields=(
                set(authoritative_hash_policy.exclude_fields)
                if authoritative_hash_policy is not None
                else set(yaml_config.content_hash.exclude)
            ),
        )
        structural_policy = build_structural_policy(
            domain_config=domain_config,
            pandera_silver_schema=pandera_silver_schema,
        )
        dependencies = build_transformer_dependencies(
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            contract_policy=contract_policy,
            structural_policy=structural_policy,
        )
        transformer = transformer_class(
            provider=self.provider,
            entity_type=entity_type,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
            **publication_vocabulary_kwargs(transformer_class),
        )
        configure_target_transformer(transformer, yaml_config, target_profile, settings)
        return transformer

    def _load_contract_policy(
        self, entity_type: str | None
    ) -> ContractPolicyProtocol | None:
        """Load policy for provider/entity and degrade gracefully when missing."""
        if entity_type is None:
            return None
        try:
            return self.contract_policy_loader(self.provider, entity_type)
        except ValueError:
            return None
