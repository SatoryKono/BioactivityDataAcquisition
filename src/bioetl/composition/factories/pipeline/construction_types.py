"""Typed protocol contracts for pipeline-construction helper modules."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.config import DQConfig, PipelineConfig
from bioetl.domain.ports import ContractPolicyPort
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


class _SchemaBuilder(Protocol):
    """Protocol for schema classes that can materialize a runtime schema."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...
