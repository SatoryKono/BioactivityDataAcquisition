"""Composite pipeline configuration models.

Defines immutable configuration objects for composite pipelines:
- SeedConfig: Seed pipeline configuration
- EnricherConfig: Single enricher configuration
- MergeConfig: Merge operation configuration
- CompositeConfig: Complete composite pipeline configuration

Aggregation configuration is defined in aggregation.py and re-exported here.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)

# Re-export aggregation types for backward compatibility
__all__ = [
    "AggregationConfig",
    "AggregationFieldSpec",
    "AggregationFunction",
    "ColumnGroupConfig",
    "CompositeConfig",
    "CompositeDQConfig",
    "DQOverrideConfig",
    "DependencyConfig",
    "DependencyConfig",
    "EnricherCardinality",
    "EnricherConfig",
    "ExecutionConfig",
    "LineageConfig",
    "MergeConfig",
    "SeedConfig",
]


@dataclass(frozen=True, slots=True)
class SeedConfig:
    """Configuration for seed pipeline in a composite.

    The seed pipeline extracts primary entities that will be
    enriched by downstream pipelines.

    Attributes:
        pipeline: Name of the seed pipeline (e.g., "chembl_publication").
        output_keys: Keys to extract for enrichment (e.g., ["doi", "pmid"]).
        silver_table: Path to seed Silver table output.
        limit: Optional limit on records to extract.

    Example:
        >>> config = SeedConfig(
        ...     pipeline="chembl_publication",
        ...     output_keys=("document_id", "doi", "pmid"),
        ...     silver_table="silver/chembl/publication",
        ... )
    """

    pipeline: str
    output_keys: tuple[str, ...]
    silver_table: str
    limit: int | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.output_keys, list):
            object.__setattr__(self, "output_keys", tuple(self.output_keys))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        _require_non_empty(self.pipeline, "seed pipeline name")
        _require_non_empty(self.output_keys, "seed output_keys")
        _require_non_empty(self.silver_table, "seed silver_table")
        _validate_positive_limit(self.limit, "seed")


@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Configuration for a dependency pipeline.

    Dependencies run after the seed but before enrichers to populate
    Silver tables that enrichers will read from. Unlike enrichers,
    dependencies execute as full standalone pipelines (API → Bronze → Silver).

    Use cases:
    - Derived entities that need full API data (e.g., publication_term from /document)
    - Pipelines with force_full_scan that don't work with enricher filtering
    - Data that must be pre-populated before enrichment phase

    Attributes:
        pipeline: Name of the dependency pipeline (e.g., "chembl_publication_term").
        join_keys: Keys to extract from seed for filtering API calls.
            Used to limit the scope of data fetched from the API.
        required: If True, failure causes composite failure.
        timeout_seconds: Maximum time for dependency execution.
        silver_table: Path to dependency's Silver table.

    Example:
        >>> config = DependencyConfig(
        ...     pipeline="chembl_publication_term",
        ...     join_keys=("document_chembl_id",),
        ...     silver_table="silver/chembl/publication_term",
        ... )
    """

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    timeout_seconds: int = 600
    silver_table: str | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        _require_non_empty(self.pipeline, "dependency pipeline name")
        _require_non_empty(self.join_keys, f"dependency {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"dependency {self.pipeline} timeout_seconds"
        )

    @property
    def primary_join_key(self) -> str:
        """Get the primary (first) join key."""
        return self.join_keys[0]


@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Configuration for a single enrichment pipeline.

    Defines how an enricher joins with seed data and handles failures.

    Attributes:
        pipeline: Name of the enricher pipeline (e.g., "crossref_publication").
        join_keys: Keys to join on from seed (e.g., ("doi",) or ("doi", "pmid")).
            Multiple keys indicate fallback chain: try doi first, then pmid.
        required: If True, failure causes composite failure.
        filter_condition: SQL-like condition to filter keys before enrichment.
            Example: "pmid IS NOT NULL" skips records without pmid.
        timeout_seconds: Maximum time for enricher execution.
        fallback_strategy: Strategy when enricher fails.
        silver_table: Path to enricher Silver table (auto-generated if None).
        limit: Optional limit on records to enrich.
        cardinality: Relationship type between enricher and seed data.
            ONE_TO_ONE (default) or MANY_TO_ONE.
        aggregation: Aggregation config for MANY_TO_ONE enrichers.
            Required when cardinality is MANY_TO_ONE.

    Example:
        >>> config = EnricherConfig(
        ...     pipeline="crossref_publication", join_keys=("doi",), required=True,
        ... )
    """

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
        """Validate and convert types."""
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
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
        """Validate configuration invariants."""
        _require_non_empty(self.pipeline, "enricher pipeline name")
        _require_non_empty(self.join_keys, f"enricher {self.pipeline} join_keys")
        _validate_positive(
            self.timeout_seconds, f"enricher {self.pipeline} timeout_seconds"
        )
        _validate_positive_limit(self.limit, f"enricher {self.pipeline}")
        # Validate cardinality/aggregation relationship
        if (
            self.cardinality == EnricherCardinality.MANY_TO_ONE
            and self.aggregation is None
        ):
            raise ValueError(
                f"Enricher '{self.pipeline}' with cardinality=many_to_one "
                "requires aggregation config"
            )

    @property
    def primary_join_key(self) -> str:
        """Get the primary (first) join key."""
        return self.join_keys[0]

    @property
    def has_fallback_keys(self) -> bool:
        """Check if fallback join keys are available."""
        return len(self.join_keys) > 1

    @property
    def is_many_to_one(self) -> bool:
        """Check if this enricher has 1:M cardinality."""
        return self.cardinality == EnricherCardinality.MANY_TO_ONE


@dataclass(frozen=True, slots=True)
class ColumnGroupConfig:
    """Configuration for a column group in output ordering.

    Defines how columns are grouped and ordered in the merged output.
    Columns can be matched by explicit field names or regex patterns.

    Attributes:
        name: Group name for logging/debugging.
        fields: Explicit list of field names to include in this group.
            Matches both exact field names and prefixed versions
            (e.g., "title" matches "title" and "crossref.title").
        pattern: Regex pattern to match field names.
            Applied after explicit field matching.
        provider_order: Order of providers within this group.
            Seed columns (no prefix) always come first.

    Example:
        >>> group = ColumnGroupConfig(
        ...     name="title",
        ...     fields=("title", "vernacular_title"),
        ...     provider_order=("chembl", "crossref", "openalex"),
        ... )
    """

    name: str
    fields: tuple[str, ...] = ()
    pattern: str | None = None
    provider_order: tuple[str, ...] = (
        "chembl",
        "crossref",
        "openalex",
        "pubmed",
        "semanticscholar",
    )

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))
        if isinstance(self.provider_order, list):
            object.__setattr__(self, "provider_order", tuple(self.provider_order))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        _require_non_empty(self.name, "column group name")
        if not self.fields and not self.pattern:
            raise ValueError(
                f"Column group '{self.name}' must have either fields or pattern"
            )


@dataclass(frozen=True, slots=True)
class MergeConfig:
    """Configuration for merge step.

    Defines how enriched data is combined into a unified output.

    Attributes:
        strategy: Join strategy for merging (left_outer, inner, union).
        conflict_resolution: Strategy for field conflicts.
        output_silver_path: Path for merged Silver table.
        output_gold_path: Path for merged Gold table.
        field_priorities: Mapping of field to source priority list.
            Used with EXPLICIT_RULES conflict resolution.
            Example: {"title": ["chembl", "crossref"]}
        field_mappings: Mapping to rename fields during merge.
            Example: {"crossref_title": "title"}

    Example:
        >>> config = MergeConfig(
        ...     strategy=MergeStrategy.LEFT_OUTER,
        ...     conflict_resolution=ConflictResolution.SEED_PRIORITY,
        ...     output_silver_path="silver/composite/publication",
        ...     output_gold_path="gold/publication_enriched",
        ... )
    """

    strategy: MergeStrategy
    conflict_resolution: ConflictResolution
    output_silver_path: str
    output_gold_path: str
    field_priorities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    field_mappings: dict[str, str] = field(default_factory=dict)
    column_groups: tuple[ColumnGroupConfig, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        self._convert_strategy()
        self._convert_conflict_resolution()
        self._convert_field_priorities()
        self._convert_column_groups()
        self._validate()

    def _convert_strategy(self) -> None:
        """Convert strategy string to enum if needed."""
        if isinstance(self.strategy, str):
            object.__setattr__(
                self, "strategy", MergeStrategy.from_string(self.strategy)
            )

    def _convert_conflict_resolution(self) -> None:
        """Convert conflict_resolution string to enum if needed."""
        if isinstance(self.conflict_resolution, str):
            object.__setattr__(
                self,
                "conflict_resolution",
                ConflictResolution.from_string(self.conflict_resolution),
            )

    def _convert_field_priorities(self) -> None:
        """Convert list values in field_priorities to tuples."""
        if self.field_priorities:
            converted = {
                k: tuple(v) if isinstance(v, list) else v
                for k, v in self.field_priorities.items()
            }
            object.__setattr__(self, "field_priorities", converted)

    def _convert_column_groups(self) -> None:
        """Convert list of column groups to tuple of ColumnGroupConfig."""
        if isinstance(self.column_groups, list):
            converted = tuple(
                ColumnGroupConfig(**g) if isinstance(g, dict) else g
                for g in self.column_groups
            )
            object.__setattr__(self, "column_groups", converted)

    def _validate(self) -> None:
        """Validate configuration invariants."""
        if not self.output_silver_path:
            raise ValueError("merge output_silver_path cannot be empty")
        if not self.output_gold_path:
            raise ValueError("merge output_gold_path cannot be empty")
        if (
            self.conflict_resolution == ConflictResolution.EXPLICIT_RULES
            and not self.field_priorities
        ):
            raise ValueError(
                "field_priorities required when using EXPLICIT_RULES conflict resolution"
            )

    def get_field_priority(self, field_name: str) -> tuple[str, ...] | None:
        """Get source priority order for a field.

        Args:
            field_name: Name of the field.

        Returns:
            Tuple of source names in priority order, or None if not configured.
        """
        return self.field_priorities.get(field_name)


@dataclass(frozen=True, slots=True)
class DQOverrideConfig:
    """DQ threshold overrides for a specific enricher.

    Allows customizing DQ thresholds per-enricher when defaults
    are too strict or lenient.

    Attributes:
        soft_fail_threshold: Override soft threshold (0.0-1.0).
        hard_fail_threshold: Override hard threshold (0.0-1.0).
    """

    soft_fail_threshold: float | None = None
    hard_fail_threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate threshold values."""
        _validate_optional_threshold(self.soft_fail_threshold, "soft_fail_threshold")
        _validate_optional_threshold(self.hard_fail_threshold, "hard_fail_threshold")
        _validate_threshold_order(self.soft_fail_threshold, self.hard_fail_threshold)


@dataclass(frozen=True, slots=True)
class CompositeDQConfig:
    """Data quality configuration for composite pipelines.

    Extends standard DQConfig with per-enricher overrides.

    Attributes:
        soft_fail_threshold: Default soft threshold for composite.
        hard_fail_threshold: Default hard threshold for composite.
        enricher_overrides: Per-enricher DQ threshold overrides.
        required_fields: Fields required in final Gold output.
    """

    soft_fail_threshold: float = 0.10
    hard_fail_threshold: float = 0.30
    enricher_overrides: dict[str, DQOverrideConfig] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.required_fields, list):
            object.__setattr__(self, "required_fields", tuple(self.required_fields))
        self._validate()

    def _validate(self) -> None:
        """Validate DQ configuration."""
        if not 0.0 <= self.soft_fail_threshold <= 1.0:
            raise ValueError(
                f"soft_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.soft_fail_threshold}"
            )
        if not 0.0 <= self.hard_fail_threshold <= 1.0:
            raise ValueError(
                f"hard_fail_threshold must be between 0.0 and 1.0, "
                f"got {self.hard_fail_threshold}"
            )
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )

    def get_enricher_soft_threshold(self, enricher_name: str) -> float:
        """Get effective soft threshold for an enricher."""
        override = self.enricher_overrides.get(enricher_name)
        if override and override.soft_fail_threshold is not None:
            return override.soft_fail_threshold
        return self.soft_fail_threshold

    def get_enricher_hard_threshold(self, enricher_name: str) -> float:
        """Get effective hard threshold for an enricher."""
        override = self.enricher_overrides.get(enricher_name)
        if override and override.hard_fail_threshold is not None:
            return override.hard_fail_threshold
        return self.hard_fail_threshold


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Execution options for composite pipeline.

    Attributes:
        max_concurrency: Maximum concurrent enrichers.
        checkpoint_enabled: Enable checkpointing for resume.
        retry_max_attempts: Max retry attempts per enricher.
        retry_backoff_multiplier: Backoff multiplier for retries.
    """

    max_concurrency: int = 4
    checkpoint_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_concurrency <= 0:
            raise ValueError(
                f"max_concurrency must be positive, got {self.max_concurrency}"
            )
        if self.retry_max_attempts < 0:
            raise ValueError(
                f"retry_max_attempts must be non-negative, got {self.retry_max_attempts}"
            )
        if self.retry_backoff_multiplier <= 0:
            raise ValueError(
                f"retry_backoff_multiplier must be positive, "
                f"got {self.retry_backoff_multiplier}"
            )


@dataclass(frozen=True, slots=True)
class LineageConfig:
    """Configuration for lineage tracking.

    Attributes:
        track_field_sources: Track which source provided each field.
        track_timestamps: Include enrichment timestamps.
        track_status: Include per-record enrichment status.
    """

    track_field_sources: bool = True
    track_timestamps: bool = True
    track_status: bool = True


@dataclass(frozen=True, slots=True)
class CompositeConfig:
    """Complete composite pipeline configuration.

    Combines all configuration aspects: seed, dependencies, enrichers, merge,
    DQ, execution options, and lineage tracking.

    This is the main configuration object loaded from YAML and
    used by CompositePipelineRunner.

    Execution order:
    1. Seed pipeline runs first
    2. Dependencies run after seed (to populate Silver tables)
    3. Enrichers run after dependencies (read from populated Silver tables)
    4. Merge combines all results

    Attributes:
        name: Composite pipeline name (e.g., "composite_publication").
        version: Configuration version (semver).
        seed: Seed pipeline configuration.
        dependencies: Tuple of dependency configurations.
            Dependencies run after seed but before enrichers to populate
            Silver tables that enrichers will read from.
        enrichers: Tuple of enricher configurations.
        merge: Merge step configuration.
        dq: Data quality configuration.
        execution: Execution options.
        lineage: Lineage tracking configuration.

    Example:
        >>> config = CompositeConfig(
        ...     name="composite_publication",
        ...     version="1.0.0",
        ...     seed=SeedConfig(...),
        ...     dependencies=(DependencyConfig(...),),
        ...     enrichers=(EnricherConfig(...), EnricherConfig(...)),
        ...     merge=MergeConfig(...),
        ... )
        >>> config.required_enrichers
        ('crossref_publication',)
    """

    name: str
    version: str
    seed: SeedConfig
    enrichers: tuple[EnricherConfig, ...]
    merge: MergeConfig
    dependencies: tuple[DependencyConfig, ...] = ()
    dq: CompositeDQConfig = field(default_factory=CompositeDQConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    lineage: LineageConfig = field(default_factory=LineageConfig)

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.enrichers, list):
            object.__setattr__(self, "enrichers", tuple(self.enrichers))
        if isinstance(self.dependencies, list):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))
        self._validate()

    def _validate(self) -> None:
        """Validate composite configuration."""
        if not self.name:
            raise ValueError("composite name cannot be empty")
        if not self.version:
            raise ValueError("composite version cannot be empty")
        if not self.enrichers:
            raise ValueError("composite must have at least one enricher")
        self._validate_join_keys()
        self._validate_dependency_join_keys()
        self._validate_unique_enrichers()
        self._validate_unique_dependencies()

    def _validate_join_keys(self) -> None:
        """Validate that enricher join keys exist in seed output_keys."""
        seed_keys = set(self.seed.output_keys)
        for enricher in self.enrichers:
            for key in enricher.join_keys:
                if key not in seed_keys:
                    raise ValueError(
                        f"Enricher {enricher.pipeline} join_key '{key}' "
                        f"not found in seed output_keys: {self.seed.output_keys}"
                    )

    def _validate_unique_enrichers(self) -> None:
        """Validate that enricher pipeline names are unique."""
        names = [e.pipeline for e in self.enrichers]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate enricher pipelines: {set(duplicates)}")

    def _validate_dependency_join_keys(self) -> None:
        """Validate that dependency join keys exist in seed output_keys."""
        seed_keys = set(self.seed.output_keys)
        for dep in self.dependencies:
            for key in dep.join_keys:
                if key not in seed_keys:
                    raise ValueError(
                        f"Dependency {dep.pipeline} join_key '{key}' "
                        f"not found in seed output_keys: {self.seed.output_keys}"
                    )

    def _validate_unique_dependencies(self) -> None:
        """Validate that dependency pipeline names are unique."""
        names = [d.pipeline for d in self.dependencies]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate dependency pipelines: {set(duplicates)}")

    @property
    def required_enrichers(self) -> tuple[str, ...]:
        """Get names of required enrichers."""
        return tuple(e.pipeline for e in self.enrichers if e.required)

    @property
    def optional_enrichers(self) -> tuple[str, ...]:
        """Get names of optional enrichers."""
        return tuple(e.pipeline for e in self.enrichers if not e.required)

    @property
    def all_enricher_names(self) -> tuple[str, ...]:
        """Get names of all enrichers."""
        return tuple(e.pipeline for e in self.enrichers)

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        """Get names of required dependencies."""
        return tuple(d.pipeline for d in self.dependencies if d.required)

    @property
    def optional_dependencies(self) -> tuple[str, ...]:
        """Get names of optional dependencies."""
        return tuple(d.pipeline for d in self.dependencies if not d.required)

    @property
    def all_dependency_names(self) -> tuple[str, ...]:
        """Get names of all dependencies."""
        return tuple(d.pipeline for d in self.dependencies)

    def get_dependency(self, pipeline_name: str) -> DependencyConfig | None:
        """Get dependency config by pipeline name."""
        for dep in self.dependencies:
            if dep.pipeline == pipeline_name:
                return dep
        return None

    def get_enricher(self, pipeline_name: str) -> EnricherConfig | None:
        """Get enricher config by pipeline name."""
        for enricher in self.enrichers:
            if enricher.pipeline == pipeline_name:
                return enricher
        return None

    @property
    def lock_key(self) -> str:
        """Generate lock key for composite pipeline."""
        return f"composite:{self.name}"

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "seed": {
                "pipeline": self.seed.pipeline,
                "output_keys": list(self.seed.output_keys),
                "silver_table": self.seed.silver_table,
            },
            "dependencies": [
                {
                    "pipeline": d.pipeline,
                    "join_keys": list(d.join_keys),
                    "required": d.required,
                    "timeout_seconds": d.timeout_seconds,
                    "silver_table": d.silver_table,
                }
                for d in self.dependencies
            ],
            "enrichers": [
                {
                    "pipeline": e.pipeline,
                    "join_keys": list(e.join_keys),
                    "required": e.required,
                    "timeout_seconds": e.timeout_seconds,
                }
                for e in self.enrichers
            ],
            "merge": {
                "strategy": self.merge.strategy.value,
                "conflict_resolution": self.merge.conflict_resolution.value,
                "output_silver_path": self.merge.output_silver_path,
                "output_gold_path": self.merge.output_gold_path,
            },
        }


# Helper validation functions to reduce cyclomatic complexity


def _require_non_empty(value: object, field_name: str) -> None:
    """Validate that a value is not empty."""
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def _validate_positive(value: int | float, field_name: str) -> None:
    """Validate that a value is positive."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


def _validate_positive_limit(limit: int | None, context: str) -> None:
    """Validate that an optional limit is positive if provided."""
    if limit is not None and limit <= 0:
        raise ValueError(f"{context} limit must be positive, got {limit}")


def _validate_optional_threshold(value: float | None, name: str) -> None:
    """Validate that an optional threshold is in [0.0, 1.0] range."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def _validate_threshold_order(soft: float | None, hard: float | None) -> None:
    """Validate that soft threshold is less than hard threshold."""
    if soft is not None and hard is not None and soft >= hard:
        raise ValueError("soft_fail_threshold must be less than hard_fail_threshold")
