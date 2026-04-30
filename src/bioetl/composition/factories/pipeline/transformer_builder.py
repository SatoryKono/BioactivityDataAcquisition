"""Transformer-construction helpers for pipeline factory wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.transformer import build_structural_policy
from bioetl.composition.factories.pipeline.construction_types import (
    ContractPolicyLoader,
    EntityTypeExtractor,
)
from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.infrastructure.config import load_pipeline_contract_policy

if TYPE_CHECKING:
    from bioetl.application.core.wiring.transformer import BaseTransformer
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.ports import ContractPolicyProtocol, MetricsPort, TracingPort
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@dataclass(frozen=True, slots=True)
class TransformerBuilder:
    """Construct transformer instances with policy/config dependencies."""

    provider: str
    pipeline_name: str
    entity_type_extractor: EntityTypeExtractor
    contract_policy_loader: ContractPolicyLoader = load_pipeline_contract_policy

    def build(
        self,
        *,
        transformer_class: type[BaseTransformer] | None,
        yaml_config: PipelineYamlConfig,
        domain_config: PipelineConfig,
        pandera_silver_schema: object | None,
        tracer: TracingPort | None,
        metrics: MetricsPort | None,
    ) -> BaseTransformer | None:
        """Build transformer instance or return ``None`` when class is absent."""
        if transformer_class is None:
            return None

        identity_service = EntityIdentityGenerator(
            content_hash_include_fields=set(yaml_config.content_hash.include) or None,
            content_hash_exclude_fields=set(yaml_config.content_hash.exclude),
        )
        entity_type = self.entity_type_extractor(self.pipeline_name)
        contract_policy = self._load_contract_policy(entity_type)
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
        return transformer_class(
            provider=self.provider,
            entity_type=entity_type,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            dependencies=dependencies,
        )

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
