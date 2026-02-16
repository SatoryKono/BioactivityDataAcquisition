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
from bioetl.domain.composite.cross_validation import (
    EnricherFieldPairing,
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
    - Pipelines with full_scan_only strategy that don't work with enricher filtering
    - Data that must be pre-populated before enrichment phase
    - Chained dependencies where one dependency provides keys for another

    Attributes:
        pipeline: Name of the dependency pipeline (e.g., "chembl_publication_term").
        join_keys: Keys to extract for filtering API calls.
            Used to limit the scope of data fetched from the API.
            For chained dependencies, these are column names in key_source table.
        required: If True, failure causes composite failure.
        timeout_seconds: Maximum time for dependency execution.
        silver_table: Path to dependency's Silver table.
        key_source: Source of join keys. Options:
            - None or "seed": Use keys from seed pipeline (default)
            - Pipeline name: Read keys from that dependency's Silver table
            This enables chained dependencies where one populates data
            that provides keys for the next.
        filter_field: Field name to use when filtering the target API.
            If None, uses the first join_key. Useful when source column name
            differs from target API field name (e.g., protein_classification_id
            in source table vs protein_class_id in API).
        filter_fields: Multiple field names for multi-field API filtering.
            When set, ALL specified fields are passed as AND-filters to the API.
            Example: ("molecule_chembl_id", "document_chembl_id") produces
            ?molecule_chembl_id__in=...&document_chembl_id__in=...
            Takes precedence over filter_field.

    Example:
        >>> # Standard dependency using seed keys
        >>> config = DependencyConfig(
        ...     pipeline="chembl_publication_term",
        ...     join_keys=("document_chembl_id",),
        ...     silver_table="silver/chembl/publication_term",
        ... )
        >>> # Chained dependency with field mapping
        >>> config = DependencyConfig(
        ...     pipeline="chembl_protein_class",
        ...     join_keys=("protein_classification_id",),  # Source column
        ...     filter_field="protein_class_id",           # Target API field
        ...     key_source="chembl_target_component",
        ...     silver_table="silver/chembl/protein_class",
        ... )
        >>> # Dual-field filtering (compound_record by molecule + document)
        >>> config = DependencyConfig(
        ...     pipeline="chembl_compound_record",
        ...     join_keys=("molecule_chembl_id", "document_chembl_id"),
        ...     filter_fields=("molecule_chembl_id", "document_chembl_id"),
        ...     silver_table="silver/chembl/compound_record",
        ... )
    """

    pipeline: str
    join_keys: tuple[str, ...]
    required: bool = False
    timeout_seconds: int = 600
    silver_table: str | None = None
    key_source: str | None = None  # None = seed, or pipeline name for chained deps
    filter_field: str | None = None  # API filter field (defaults to first join_key)
    filter_fields: tuple[str, ...] | None = (
        None  # Multi-field API filtering (AND logic)
    )
    key_filter: str | None = None  # SQL-like condition to filter key_source records

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.join_keys, list):
            object.__setattr__(self, "join_keys", tuple(self.join_keys))
        if isinstance(self.filter_fields, list):
            object.__setattr__(self, "filter_fields", tuple(self.filter_fields))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
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
        """Get the primary (first) join key."""
        return self.join_keys[0]

    @property
    def uses_seed_keys(self) -> bool:
        """Check if this dependency uses keys from seed (default behavior)."""
        return self.key_source is None or self.key_source == "seed"

    @property
    def effective_filter_fields(self) -> tuple[str, ...]:
        """Resolve effective filter fields.

        Priority: filter_fields > filter_field > first join_key.
        """
        if self.filter_fields:
            return self.filter_fields
        if self.filter_field:
            return (self.filter_field,)
        return (self.join_keys[0],)

    @property
    def is_multi_field_filter(self) -> bool:
        """Check if this dependency uses multi-field API filtering."""
        return len(self.effective_filter_fields) > 1


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


def _coerce_to_tuple(obj: object, attr: str) -> None:
    """Coerce a list attribute to tuple on a frozen dataclass."""
    val = getattr(obj, attr, None)
    if val is not None and isinstance(val, list):
        object.__setattr__(obj, attr, tuple(val))


def _coerce_column_groups(obj: object, attr: str) -> None:
    """Coerce column_groups list to tuple of ColumnGroupConfig."""
    val = getattr(obj, attr, None)
    if val is not None and isinstance(val, list):
        object.__setattr__(
            obj,
            attr,
            tuple(ColumnGroupConfig(**g) if isinstance(g, dict) else g for g in val),
        )


@dataclass(frozen=True, slots=True)
class LayerColumnConfig:
    """Column configuration for a single medallion layer (Silver or Gold).

    Supports three modes:
    1. Explicit column list (columns parameter)
    2. Filtering existing groups (include_groups/exclude_fields)
    3. Layer-specific column groups (column_groups parameter)

    Attributes:
        columns: Explicit list of columns for this layer.
            Takes precedence over other configuration.
        column_groups: Layer-specific column groups.
            If provided, overrides shared column_groups for this layer.
        include_groups: Filter shared column_groups by group names.
            Only groups with names in this list are included.
        exclude_fields: Fields to exclude after group/pattern matching.
            Supports glob patterns (e.g., "_dq_*", "*_internal").
        rename_fields: Mapping of old_name -> new_name for renaming columns.
            Applied after filtering but before ordering.

            IMPORTANT: For Gold layer, use column names AFTER silver.rename_fields.
            Gold reads from Silver, so renames must reference Silver output schema.

            Example with rename chain:
                silver:
                  rename_fields: {"document_chembl_id": "chembl_doc_id"}
                gold:
                  rename_fields: {"chembl_doc_id": "publication_id"}
                  # ↑ Uses Silver output name, not original!

    Example:
        >>> # Explicit columns for Gold layer
        >>> gold_config = LayerColumnConfig(
        ...     columns=("entity_id", "doi", "title", "year"),
        ... )
        >>> # Filter by groups with renaming
        >>> gold_config = LayerColumnConfig(
        ...     include_groups=("system", "identifiers", "title", "year"),
        ...     exclude_fields=("abstract", "_dq_*"),
        ...     rename_fields={"_run_id": "pipeline_run_id", "pmid": "pubmed_id"},
        ... )
    """

    columns: tuple[str, ...] | None = None
    column_groups: tuple[ColumnGroupConfig, ...] | None = None
    include_groups: tuple[str, ...] | None = None
    exclude_fields: tuple[str, ...] | None = None
    rename_fields: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and convert types."""
        _coerce_to_tuple(self, "columns")
        _coerce_to_tuple(self, "include_groups")
        _coerce_to_tuple(self, "exclude_fields")
        _coerce_column_groups(self, "column_groups")
        if not isinstance(self.rename_fields, dict):
            object.__setattr__(self, "rename_fields", dict(self.rename_fields))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        # At most one of: columns, include_groups, column_groups
        modes = sum(
            [
                self.columns is not None,
                self.include_groups is not None,
                self.column_groups is not None,
            ]
        )
        if modes > 1:
            raise ValueError(
                "LayerColumnConfig: only one of columns/include_groups/column_groups allowed"
            )


@dataclass(frozen=True, slots=True)
class DataSchemaConfig:
    """Multi-layer column schema configuration.

    Defines column ordering and filtering for different medallion layers.
    Supports backward compatibility with shared column_groups.

    Attributes:
        column_groups: Shared column groups for all layers (legacy/default).
        silver: Silver layer-specific column configuration.
        gold: Gold layer-specific column configuration.

    Resolution order:
    1. If layer.columns is set → use explicit list
    2. If layer.include_groups is set → filter shared column_groups
    3. If layer.column_groups is set → use layer-specific groups
    4. Otherwise → use shared column_groups

    Example:
        >>> # Backward compatible (shared groups)
        >>> config = DataSchemaConfig(
        ...     column_groups=(ColumnGroupConfig(...), ...),
        ... )
        >>> # Layer-specific filtering
        >>> config = DataSchemaConfig(
        ...     column_groups=(ColumnGroupConfig(...), ...),
        ...     silver=LayerColumnConfig(
        ...         include_groups=("system", "identifiers", "title", "abstract"),
        ...     ),
        ...     gold=LayerColumnConfig(
        ...         include_groups=("system", "identifiers", "title"),
        ...         exclude_fields=("_dq_*", "_composite_*"),
        ...     ),
        ... )
    """

    column_groups: tuple[ColumnGroupConfig, ...] = ()
    silver: LayerColumnConfig | None = None
    gold: LayerColumnConfig | None = None

    def __post_init__(self) -> None:
        """Validate and convert types."""
        _coerce_column_groups(self, "column_groups")
        if isinstance(self.silver, dict):
            object.__setattr__(self, "silver", LayerColumnConfig(**self.silver))
        if isinstance(self.gold, dict):
            object.__setattr__(self, "gold", LayerColumnConfig(**self.gold))

    def get_layer_groups(self, layer: str) -> tuple[ColumnGroupConfig, ...]:
        """Get effective column groups for a layer.

        Args:
            layer: Layer name ("silver" or "gold").

        Returns:
            Tuple of ColumnGroupConfig for the layer.
            Returns layer-specific groups if defined, otherwise shared groups.
        """
        layer_config: LayerColumnConfig | None = getattr(self, layer, None)
        if layer_config and layer_config.column_groups:
            return layer_config.column_groups
        return self.column_groups

    def should_include_group(self, layer: str, group_name: str) -> bool:
        """Check if a group should be included for a layer.

        Args:
            layer: Layer name ("silver" or "gold").
            group_name: Name of the column group.

        Returns:
            True if group should be included, False otherwise.
        """
        layer_config = getattr(self, layer, None)
        if not layer_config or not layer_config.include_groups:
            return True  # No filter → include all groups
        return group_name in layer_config.include_groups


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
        exclude_fields: Columns to drop from merged output.
            Supports exact names and glob patterns.
        preserve_all_sources: If True, keep all provider-qualified columns
            for common fields instead of coalescing them. Default: False.
            When enabled, columns like chembl.publication.title and
            crossref.publication.title are both preserved in the output.

    Example:
        >>> config = MergeConfig(
        ...     strategy=MergeStrategy.LEFT_OUTER,
        ...     conflict_resolution=ConflictResolution.SEED_PRIORITY,
        ...     output_silver_path="silver/composite/publication",
        ...     output_gold_path="gold/publication_enriched",
        ...     preserve_all_sources=True,  # Keep all provider columns
        ... )
    """

    strategy: MergeStrategy
    conflict_resolution: ConflictResolution
    output_silver_path: str
    output_gold_path: str
    field_priorities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    field_mappings: dict[str, str] = field(default_factory=dict)
    column_groups: tuple[ColumnGroupConfig, ...] = ()
    exclude_fields: tuple[str, ...] = ()
    preserve_all_sources: bool = False

    def __post_init__(self) -> None:
        """Validate and convert types."""
        self._convert_strategy()
        self._convert_conflict_resolution()
        self._convert_field_priorities()
        self._convert_column_groups()
        self._convert_exclude_fields()
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

    def _convert_exclude_fields(self) -> None:
        """Convert list of exclude_fields to tuple."""
        if isinstance(self.exclude_fields, list):
            object.__setattr__(self, "exclude_fields", tuple(self.exclude_fields))

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
        provider_lookup_fields: Per-provider mapping of lookup metadata field names.
        track_source_for_fields: Field names requiring source tracking for overlapping data.
    """

    track_field_sources: bool = True
    track_timestamps: bool = True
    track_status: bool = True
    provider_lookup_fields: dict[str, dict[str, str]] = field(default_factory=dict)
    track_source_for_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CrossValidationConfig:
    """Configuration for pre-merge cross-validation of seed vs enricher data.

    Cross-validation compares paired fields between seed and each enricher
    before merge. Mismatches are counted per record:
    - 0 mismatches: PASS
    - 1 mismatch: WARNING (configurable via warning_threshold)
    - 2+ mismatches: ENRICHER_ERROR, all enricher fields nullified
    - 2+ enrichers with ENRICHER_ERROR: seed record quarantined

    Attributes:
        enabled: Whether cross-validation is active. Default True.
        warning_threshold: Number of mismatches to trigger WARNING. Default 1.
        error_threshold: Number of mismatches to trigger ENRICHER_ERROR. Default 2.
        quarantine_threshold: Number of enricher errors to quarantine seed. Default 2.
        fuzzy_threshold: Jaccard similarity threshold for fuzzy comparisons.
        numeric_tolerance: Relative tolerance for numeric comparisons (0.10 = 10%).
        enricher_pairings: Field comparison specs per enricher.
    """

    enabled: bool = True
    warning_threshold: int = 1
    error_threshold: int = 2
    quarantine_threshold: int = 2
    fuzzy_threshold: float = 0.8
    numeric_tolerance: float = 0.10
    enricher_pairings: tuple[EnricherFieldPairing, ...] = ()

    def __post_init__(self) -> None:
        """Validate and convert types."""
        if isinstance(self.enricher_pairings, list):
            object.__setattr__(self, "enricher_pairings", tuple(self.enricher_pairings))
        self._validate()

    def _validate(self) -> None:
        """Validate configuration invariants."""
        self._validate_thresholds()
        self._validate_tolerances()

    def _validate_thresholds(self) -> None:
        """Validate threshold ordering invariants."""
        if self.warning_threshold < 1:
            raise ValueError(
                f"warning_threshold must be >= 1, got {self.warning_threshold}"
            )
        if self.error_threshold < 2:
            raise ValueError(
                f"error_threshold must be >= 2, got {self.error_threshold}"
            )
        if self.warning_threshold >= self.error_threshold:
            raise ValueError("warning_threshold must be < error_threshold")
        if self.quarantine_threshold < 1:
            raise ValueError(
                f"quarantine_threshold must be >= 1, got {self.quarantine_threshold}"
            )

    def _validate_tolerances(self) -> None:
        """Validate fuzzy and numeric tolerance ranges."""
        if not 0.0 < self.fuzzy_threshold <= 1.0:
            raise ValueError(
                f"fuzzy_threshold must be in (0.0, 1.0], got {self.fuzzy_threshold}"
            )
        if not 0.0 < self.numeric_tolerance <= 1.0:
            raise ValueError(
                f"numeric_tolerance must be in (0.0, 1.0], got {self.numeric_tolerance}"
            )

    def get_pairing(self, enricher_pipeline: str) -> EnricherFieldPairing | None:
        """Get field pairing for a specific enricher."""
        for pairing in self.enricher_pairings:
            if pairing.enricher_pipeline == enricher_pipeline:
                return pairing
        return None


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
        cross_validation: Cross-validation configuration for pre-merge checks.

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
    cross_validation: CrossValidationConfig = field(
        default_factory=CrossValidationConfig
    )

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
        if not self.enrichers and not self.dependencies:
            raise ValueError("composite must have at least one enricher or dependency")
        self._validate_join_keys()
        self._validate_dependency_join_keys()
        self._validate_unique_enrichers()
        self._validate_unique_dependencies()

    def _validate_join_keys(self) -> None:
        """Validate that enricher join keys exist in seed output_keys."""
        if not self.enrichers:
            return  # Skip if no enrichers
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
        if not self.enrichers:
            return  # Skip if no enrichers
        seen: set[str] = set()
        duplicates: set[str] = set()
        for e in self.enrichers:
            (duplicates if e.pipeline in seen else seen).add(e.pipeline)
        if duplicates:
            raise ValueError(f"Duplicate enricher pipelines: {duplicates}")

    def _validate_dependency_join_keys(self) -> None:
        """Validate that dependency join keys exist in seed output_keys.

        For chained dependencies (key_source != None and != "seed"),
        join_keys are taken from the key_source's Silver table,
        so they are NOT validated against seed output_keys.
        """
        seed_keys = set(self.seed.output_keys)
        for dep in self.dependencies:
            # Skip validation for chained dependencies
            if not dep.uses_seed_keys:
                continue
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
                    **(
                        {"filter_fields": list(d.filter_fields)}
                        if d.filter_fields
                        else {}
                    ),
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
