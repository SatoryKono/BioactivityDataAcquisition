"""Composite pipeline configuration dataclass models."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
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
from bioetl.domain.composite.config_cross_validation import CrossValidationConfig
from bioetl.domain.composite.config_dq import CompositeDQConfig, DQOverrideConfig
from bioetl.domain.composite.config_merge import MergeConfig
from bioetl.domain.composite.config_runtime import ExecutionConfig, LineageConfig
from bioetl.domain.composite.config_schema import DataSchemaConfig, LayerColumnConfig
from bioetl.domain.composite.config_validators import (
    _coerce_to_tuple,
    _require_non_empty,
    _validate_positive,
    _validate_positive_limit,
)
from bioetl.domain.composite.strategy import FallbackStrategy

__all__ = [
    "CompositeConfig",
    "CompositeDQConfig",
    "CrossValidationConfig",
    "DQOverrideConfig",
    "DataSchemaConfig",
    "DependencyConfig",
    "EnricherConfig",
    "ExecutionConfig",
    "LayerColumnConfig",
    "LineageConfig",
    "MergeConfig",
    "SeedConfig",
]


@dataclass(frozen=True, slots=True)
class SeedConfig:
    """Seed pipeline settings."""

    pipeline: str
    output_keys: tuple[str, ...]
    silver_table: str
    limit: int | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "output_keys")
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "seed pipeline name")
        _require_non_empty(self.output_keys, "seed output_keys")
        _require_non_empty(self.silver_table, "seed silver_table")
        _validate_positive_limit(self.limit, "seed")


@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Dependency pipeline settings for composite joins."""

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    timeout_seconds: int = 600
    silver_table: str | None = None
    key_source: str | None = None
    filter_field: str | None = None
    filter_fields: tuple[str, ...] | None = None
    key_filter: str | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "join_keys")
        _coerce_to_tuple(self, "filter_fields")
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "dependency pipeline name")
        _require_non_empty(self.join_keys, f"dependency {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"dependency {self.pipeline} timeout_seconds"
        )
        if self.filter_fields and self.filter_field:
            raise ValueError(
                f"Dependency {self.pipeline}: filter_fields and filter_field "
                "are mutually exclusive. Use filter_fields for multi-field filtering."
            )

    @property
    def primary_join_key(self) -> str:
        """Return the first join key used as the primary filter field."""
        return self.join_keys[0]

    @property
    def uses_seed_keys(self) -> bool:
        """Return True if this dependency uses seed pipeline keys for filtering."""
        return self.key_source is None or self.key_source == "seed"

    @property
    def effective_filter_fields(self) -> tuple[str, ...]:
        """Return the resolved set of filter fields for this dependency.

        Resolves precedence: ``filter_fields`` > ``filter_field`` > first join key.
        """
        if self.filter_fields:
            return self.filter_fields
        if self.filter_field:
            return (self.filter_field,)
        return (self.join_keys[0],)

    @property
    def is_multi_field_filter(self) -> bool:
        """Return True if more than one effective filter field is active."""
        return len(self.effective_filter_fields) > 1


@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Enricher pipeline settings for composite joins."""

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    filter_condition: str | None = None
    timeout_seconds: int = 600
    fallback_strategy: FallbackStrategy = FallbackStrategy.SKIP
    silver_table: str | None = None
    limit: int | None = None
    cardinality: EnricherCardinality = EnricherCardinality.ONE_TO_ONE
    aggregation: AggregationConfig | None = None

    def __post_init__(self) -> None:
        _coerce_to_tuple(self, "join_keys")
        if isinstance(self.fallback_strategy, str):
            object.__setattr__(
                self,
                "fallback_strategy",
                FallbackStrategy.from_string(self.fallback_strategy),
            )
        if isinstance(self.cardinality, str):
            object.__setattr__(
                self,
                "cardinality",
                EnricherCardinality.from_string(self.cardinality),
            )
        if isinstance(self.aggregation, dict):
            object.__setattr__(
                self,
                "aggregation",
                AggregationConfig(**self.aggregation),
            )
        self._validate()

    def _validate(self) -> None:
        _require_non_empty(self.pipeline, "enricher pipeline name")
        _require_non_empty(self.join_keys, f"enricher {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"enricher {self.pipeline} timeout_seconds"
        )
        _validate_positive_limit(self.limit, f"enricher {self.pipeline}")
        if (
            self.cardinality == EnricherCardinality.MANY_TO_ONE
            and self.aggregation is None
        ):
            raise ValueError(
                f"Enricher '{self.pipeline}' with cardinality=many_to_one requires aggregation config"
            )

    @property
    def primary_join_key(self) -> str:
        """Return the first join key used as the primary enrichment join field."""
        return self.join_keys[0]

    @property
    def has_fallback_keys(self) -> bool:
        """Return True if secondary join keys are available for fallback matching."""
        return len(self.join_keys) > 1

    @property
    def is_many_to_one(self) -> bool:
        """Return True if this enricher has many-to-one cardinality (requires aggregation)."""
        return self.cardinality == EnricherCardinality.MANY_TO_ONE

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
        """Return the runtime lock key for this composite pipeline."""
        return f"composite:{self.name}"

    def to_dict(self) -> dict[str, object]:
        """Serialize this config to a plain dictionary."""
        return _composite_to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CompositeConfig:
        """Deserialize a CompositeConfig from a plain dictionary."""
        return _composite_from_dict(
            data,
            composite_cls=cls,
            seed_cls=SeedConfig,
            dependency_cls=DependencyConfig,
            enricher_cls=EnricherConfig,
            merge_cls=MergeConfig,
        )
