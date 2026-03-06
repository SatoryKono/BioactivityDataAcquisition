"""Construction helpers for pipeline factory orchestration.

Extracts context/config/transformer construction concerns from
``create_pipeline_with_services`` to keep orchestration thin.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.config import (
    load_pipeline_contract_policy,
    yaml_config_to_domain,
)
from bioetl.infrastructure.config.pipeline_config_loader import PipelineConfigLoader

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import ContractPolicyPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class EntityTypeExtractor(Protocol):
    """Callable contract for deriving entity type from pipeline name."""

    def __call__(self, pipeline_name: str) -> str | None:
        """Resolve entity type from pipeline name."""
        ...


class DomainConfigMapper(Protocol):
    """Callable contract for mapping YAML config to domain config."""

    def __call__(
        self,
        yaml_config: PipelineYamlConfig,
        resolved_dq_config: DQConfig | None = None,
    ) -> PipelineConfig:
        """Map YAML config to domain PipelineConfig."""
        ...


class ContractPolicyLoader(Protocol):
    """Callable contract for loading pipeline contract policy."""

    def __call__(self, provider: str, entity: str) -> ContractPolicyPort:
        """Load contract policy for provider/entity."""
        ...


@dataclass(frozen=True, slots=True)
class RunContextFactory:
    """Build ``RunContext`` for metadata coordinator wiring."""

    pipeline_name: str
    provider: str
    entity_type_extractor: EntityTypeExtractor
    pipeline_version_getter: Callable[[PipelineYamlConfig], str] = get_pipeline_version
    git_commit_getter: Callable[[], str | None] = get_git_commit
    config_hash_getter: Callable[[PipelineYamlConfig], str] = compute_config_hash

    def create(
        self,
        *,
        run_id: RunID,
        runtime: RuntimeConfig,
        yaml_config: PipelineYamlConfig,
    ) -> RunContext:
        """Create metadata ``RunContext`` from runtime and resolved YAML.

        Returns:
            RunContext populated with run ID, type, provider, entity, and versioning.
        """
        entity = self.entity_type_extractor(self.pipeline_name) or self.pipeline_name
        return RunContext.create(
            run_id=run_id,
            run_type=runtime.run_type,
            started_at=datetime.now(UTC),
            provider=self.provider,
            entity=entity,
            pipeline_version=self.pipeline_version_getter(yaml_config),
            git_commit=self.git_commit_getter(),
            config_hash=self.config_hash_getter(yaml_config),
        )


@dataclass(frozen=True, slots=True)
class DomainConfigResolver:
    """Resolve domain config with hierarchical DQ integration."""

    configs_root: Path = Path("configs")
    loader_class: type[PipelineConfigLoader] = PipelineConfigLoader
    domain_mapper: DomainConfigMapper = yaml_config_to_domain

    def resolve(
        self,
        yaml_config: PipelineYamlConfig,
        *,
        relaxed_dq: bool,
    ) -> PipelineConfig:
        """Resolve domain config from YAML with DQ loader composition.

        Returns:
            Resolved domain PipelineConfig with integrated DQ configuration.
        """
        config_loader = self.loader_class(self.configs_root, relaxed_dq=relaxed_dq)
        resolved_dq = config_loader.resolve_dq_config(yaml_config)
        return self.domain_mapper(yaml_config, resolved_dq_config=resolved_dq)


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
        tracer: TracingPort | None,
        metrics: MetricsPort | None,
    ) -> BaseTransformer | None:
        """Build transformer instance or return ``None`` when class is absent.

        Returns:
            Configured BaseTransformer with identity and contract policy, or None.
        """
        if transformer_class is None:
            return None

        identity_service = IdentityService(
            content_hash_include_fields=set(yaml_config.content_hash.include) or None,
            content_hash_exclude_fields=set(yaml_config.content_hash.exclude),
        )
        entity_type = self.entity_type_extractor(self.pipeline_name)
        contract_policy = self._load_contract_policy(entity_type)
        return transformer_class(
            provider=self.provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=domain_config.silver_filters,
            gold_filters=domain_config.gold_filters,
            identity_service=identity_service,
            contract_policy=contract_policy,
        )

    def _load_contract_policy(
        self, entity_type: str | None
    ) -> ContractPolicyPort | None:
        """Load policy for provider/entity and degrade gracefully when missing."""
        if entity_type is None:
            return None
        try:
            return self.contract_policy_loader(self.provider, entity_type)
        except ValueError:
            return None
