"""Typed protocol contracts for pipeline-construction helper modules."""

from __future__ import annotations

from typing import Protocol

from bioetl.composition.factories.pipeline.entity_type_extractor import (
    EntityTypeExtractor,
)
from bioetl.domain.config import DQConfig, PipelineConfig
from bioetl.domain.ports import ContractPolicyProtocol
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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

    def __call__(self, provider: str, entity: str) -> ContractPolicyProtocol:
        """Load contract policy for provider/entity."""
        ...


class _SchemaBuilder(Protocol):
    """Protocol for schema classes that can materialize a runtime schema."""

    @classmethod
    def to_schema(cls) -> object:
        """Materialize schema representation."""
        ...


__all__ = [
    "ContractPolicyLoader",
    "DomainConfigMapper",
    "EntityTypeExtractor",
    "_SchemaBuilder",
]
