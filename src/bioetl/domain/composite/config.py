"""Backward-compatible facade for composite configuration domain models.

Public API remains stable at ``bioetl.domain.composite.config`` while
implementation details are split into focused modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config_composite_serialization import (
    composite_from_dict as _composite_from_dict,
)
from bioetl.domain.composite.config_composite_serialization import (
    composite_to_dict as _composite_to_dict,
)
from bioetl.domain.composite.config_composite_validation import (
    coerce_composite_collections as _coerce_composite_collections,
)
from bioetl.domain.composite.config_composite_validation import (
    validate_composite_config as _validate_composite_config,
)
from bioetl.domain.composite.config_dq import CompositeDQConfig, DQOverrideConfig
from bioetl.domain.composite.config_merge import ColumnGroupConfig, MergeConfig
from bioetl.domain.composite.config_models import (
    CrossValidationConfig,
    DataSchemaConfig,
    DependencyConfig,
    EnricherConfig,
    LayerColumnConfig,
    SeedConfig,
)
from bioetl.domain.composite.config_runtime import ExecutionConfig, LineageConfig
from bioetl.domain.composite.config_validators import (
    _require_non_empty as _require_non_empty_impl,
)
from bioetl.domain.composite.config_validators import (
    _validate_optional_threshold as _validate_optional_threshold_impl,
)
from bioetl.domain.composite.config_validators import (
    _validate_positive as _validate_positive_impl,
)
from bioetl.domain.composite.config_validators import (
    _validate_positive_limit as _validate_positive_limit_impl,
)
from bioetl.domain.composite.config_validators import (
    _validate_threshold_order as _validate_threshold_order_impl,
)
from bioetl.domain.composite.cross_validation import EnricherFieldPairing

__all__ = [
    "AggregationConfig",
    "AggregationFieldSpec",
    "AggregationFunction",
    "ColumnGroupConfig",
    "CompositeConfig",
    "CompositeDQConfig",
    "CrossValidationConfig",
    "DQOverrideConfig",
    "DataSchemaConfig",
    "DependencyConfig",
    "EnricherCardinality",
    "EnricherConfig",
    "EnricherFieldPairing",
    "ExecutionConfig",
    "LayerColumnConfig",
    "LineageConfig",
    "MergeConfig",
    "SeedConfig",
]


@dataclass(frozen=True, slots=True)
class CompositeConfig:
    """Complete composite pipeline configuration root."""

    name: str
    version: str
    seed: SeedConfig
    enrichers: tuple[EnricherConfig, ...]
    merge: MergeConfig
    dependencies: tuple[DependencyConfig, ...] = ()
    dq: CompositeDQConfig = field(default_factory=CompositeDQConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    lineage: LineageConfig = field(default_factory=LineageConfig)
    cross_validation: CrossValidationConfig = field(
        default_factory=CrossValidationConfig
    )

    def __post_init__(self) -> None:
        _coerce_composite_collections(self)
        _validate_composite_config(self)

    @property
    def required_enrichers(self) -> tuple[str, ...]:
        """Return pipeline names of required enrichers."""
        return tuple(
            enricher.pipeline for enricher in self.enrichers if enricher.required
        )

    @property
    def optional_enrichers(self) -> tuple[str, ...]:
        """Return pipeline names of optional enrichers."""
        return tuple(
            enricher.pipeline for enricher in self.enrichers if not enricher.required
        )

    @property
    def all_enricher_names(self) -> tuple[str, ...]:
        """Return all enricher pipeline names (required and optional)."""
        return tuple(enricher.pipeline for enricher in self.enrichers)

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        """Return pipeline names of required dependencies."""
        return tuple(
            dependency.pipeline
            for dependency in self.dependencies
            if dependency.required
        )

    @property
    def optional_dependencies(self) -> tuple[str, ...]:
        """Return pipeline names of optional dependencies."""
        return tuple(
            dependency.pipeline
            for dependency in self.dependencies
            if not dependency.required
        )

    @property
    def all_dependency_names(self) -> tuple[str, ...]:
        """Return all dependency pipeline names."""
        return tuple(dependency.pipeline for dependency in self.dependencies)

    def get_dependency(self, pipeline_name: str) -> DependencyConfig | None:
        """Look up a dependency config by pipeline name."""
        for dependency in self.dependencies:
            if dependency.pipeline == pipeline_name:
                return dependency
        return None

    def get_enricher(self, pipeline_name: str) -> EnricherConfig | None:
        """Look up an enricher config by pipeline name."""
        for enricher in self.enrichers:
            if enricher.pipeline == pipeline_name:
                return enricher
        return None

    @property
    def lock_key(self) -> str:
        """Return the distributed lock key for this composite pipeline."""
        return f"composite:{self.name}"

    def to_dict(self) -> dict[str, object]:
        """Serialize this config to a plain dictionary."""
        return _composite_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CompositeConfig:
        """Deserialize a CompositeConfig from a plain dictionary."""
        return _composite_from_dict(data)


def _require_non_empty(value: object, field_name: str) -> None:
    """Compatibility wrapper for validation helper re-export."""
    _require_non_empty_impl(value, field_name)


def _validate_positive(value: int, field_name: str) -> None:
    """Compatibility wrapper for validation helper re-export."""
    _validate_positive_impl(value, field_name)


def _validate_positive_limit(value: int | None, context: str) -> None:
    """Compatibility wrapper for validation helper re-export."""
    _validate_positive_limit_impl(value, context)


def _validate_optional_threshold(value: float | None, name: str) -> None:
    """Compatibility wrapper for validation helper re-export."""
    _validate_optional_threshold_impl(value, name)


def _validate_threshold_order(soft: float | None, hard: float | None) -> None:
    """Compatibility wrapper for validation helper re-export."""
    _validate_threshold_order_impl(soft, hard)
