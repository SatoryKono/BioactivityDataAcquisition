"""Pydantic schemas for composite pipeline configuration files.

Validates composite pipeline YAML files (configs/pipelines/composite/*.yaml)
before converting to domain objects. Implements ADR-026 Composite Pipeline Pattern.

Usage:
    >>> schema = CompositeConfigFileSchema.model_validate(yaml_data)
    >>> domain_config = schema.to_domain()
"""

from __future__ import annotations

import warnings
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    CompositeConfig,
    CompositeDQConfig,
    CrossValidationConfig,
    DependencyConfig,
    DQOverrideConfig,
    EnricherConfig,
    ExecutionConfig,
    LineageConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)


class AggregationFieldSchema(BaseModel):
    """Pydantic schema for aggregation field specification.

    Defines how to aggregate a single field from a 1:M enricher.
    """

    source: str = Field(
        ..., min_length=1, description="Source column name to aggregate"
    )
    agg: Literal["collect_list", "collect_set", "count", "first", "concat_str"] = Field(
        ..., description="Aggregation function to apply"
    )
    filter: str | None = Field(
        default=None,
        description="Optional filter condition (e.g., \"term_type == 'MESH'\")",
    )

    def to_domain(self, output_field: str) -> AggregationFieldSpec:
        """Convert to domain AggregationFieldSpec.

        Args:
            output_field: The output field name (from the dict key).

        Returns:
            Domain AggregationFieldSpec object.
        """
        return AggregationFieldSpec(
            source_field=self.source,
            agg_function=AggregationFunction.from_string(self.agg),
            filter_condition=self.filter,
            output_field=output_field,
        )


class AggregationSchema(BaseModel):
    """Pydantic schema for 1:M enricher aggregation config.

    Defines how to aggregate multiple rows per join key into a single row.
    """

    group_by: str = Field(..., min_length=1, description="Join key to group by")
    fields: dict[str, AggregationFieldSchema] = Field(
        ..., min_length=1, description="Map of output_field -> aggregation spec"
    )

    def to_domain(self) -> AggregationConfig:
        """Convert to domain AggregationConfig."""
        return AggregationConfig(
            group_by=self.group_by,
            fields=tuple(
                spec.to_domain(output_field=name) for name, spec in self.fields.items()
            ),
        )


class SeedSchema(BaseModel):
    """Pydantic schema for seed pipeline configuration."""

    pipeline: str = Field(..., min_length=1, description="Name of the seed pipeline")
    output_keys: list[str] = Field(
        ..., min_length=1, description="Keys to extract for enrichment"
    )
    silver_table: str = Field(
        ..., min_length=1, description="Path to seed Silver table output"
    )
    limit: int | None = Field(
        default=None, gt=0, description="Optional limit on records to extract"
    )

    @field_validator("output_keys")
    @classmethod
    def validate_output_keys_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure output_keys contains valid strings."""
        if not v:
            raise ValueError("output_keys cannot be empty")
        for key in v:
            if not key or not key.strip():
                raise ValueError("output_keys cannot contain empty strings")
        return v

    def to_domain(self) -> SeedConfig:
        """Convert to immutable domain SeedConfig."""
        return SeedConfig(
            pipeline=self.pipeline,
            output_keys=tuple(self.output_keys),
            silver_table=self.silver_table,
            limit=self.limit,
        )


class DependencySchema(BaseModel):
    """Pydantic schema for dependency pipeline configuration.

    Dependencies run after seed but before enrichers to populate Silver tables.

    Supports chained dependencies via `key_source`:
    - None or "seed": Extract join_keys from seed output (default behavior)
    - "<pipeline_name>": Extract join_keys from that pipeline's Silver table
      (useful when join keys come from enrichers, not seed)
    """

    pipeline: str = Field(
        ..., min_length=1, description="Name of the dependency pipeline"
    )
    join_keys: list[str] = Field(
        ..., min_length=1, description="Keys to extract from key_source for filtering"
    )
    required: bool = Field(
        default=False, description="If True, failure causes composite failure"
    )
    timeout_seconds: int = Field(
        default=600,
        gt=0,
        description="Maximum time for dependency execution in seconds",
    )
    silver_table: str | None = Field(
        default=None, description="Path to dependency's Silver table"
    )
    key_source: str | None = Field(
        default=None,
        description=(
            "Source of join keys: None/'seed' for seed keys, "
            "or pipeline name for chained dependencies"
        ),
    )
    filter_field: str | None = Field(
        default=None,
        description=(
            "Field name to use when filtering the target API. "
            "Defaults to first join_key. Useful when source column differs "
            "from target API field (e.g., protein_classification_id vs protein_class_id)"
        ),
    )
    filter_fields: list[str] | None = Field(
        default=None,
        description=(
            "Multiple field names for multi-field API filtering (AND logic). "
            "When set, ALL specified fields are passed as filters to the API. "
            "Example: ['molecule_chembl_id', 'document_chembl_id'] produces "
            "?molecule_chembl_id__in=...&document_chembl_id__in=... "
            "Mutually exclusive with filter_field."
        ),
    )
    key_filter: str | None = Field(
        default=None,
        description=(
            "SQL-like condition to filter records from key_source before extracting join keys. "
            "Example: \"mapping_status = 'found'\" to only fetch successfully mapped IDs."
        ),
    )

    @field_validator("join_keys")
    @classmethod
    def validate_join_keys_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure join_keys contains valid strings."""
        if not v:
            raise ValueError("join_keys cannot be empty")
        for key in v:
            if not key or not key.strip():
                raise ValueError("join_keys cannot contain empty strings")
        return v

    @model_validator(mode="after")
    def validate_filter_fields_exclusive(self) -> Self:
        """Ensure filter_field and filter_fields are mutually exclusive."""
        if self.filter_field and self.filter_fields:
            raise ValueError(
                "filter_field and filter_fields are mutually exclusive. "
                "Use filter_fields for multi-field filtering."
            )
        return self

    def to_domain(self) -> DependencyConfig:
        """Convert to immutable domain DependencyConfig."""
        return DependencyConfig(
            pipeline=self.pipeline,
            join_keys=tuple(self.join_keys),
            required=self.required,
            timeout_seconds=self.timeout_seconds,
            silver_table=self.silver_table,
            key_source=self.key_source,
            filter_field=self.filter_field,
            filter_fields=tuple(self.filter_fields) if self.filter_fields else None,
            key_filter=self.key_filter,
        )


class EnricherSchema(BaseModel):
    """Pydantic schema for enricher pipeline configuration."""

    pipeline: str = Field(
        ..., min_length=1, description="Name of the enricher pipeline"
    )
    join_keys: list[str] = Field(
        ..., min_length=1, description="Keys to join on from seed"
    )
    required: bool = Field(
        default=False, description="If True, failure causes composite failure"
    )
    filter_condition: str | None = Field(
        default=None, description="SQL-like condition to filter keys"
    )
    timeout_seconds: int = Field(
        default=600, gt=0, description="Maximum time for enricher execution in seconds"
    )
    fallback_strategy: Literal["skip", "use_cached", "fail"] = Field(
        default="skip", description="Strategy when enricher fails"
    )
    silver_table: str | None = Field(
        default=None, description="Path to enricher Silver table"
    )
    limit: int | None = Field(
        default=None, gt=0, description="Optional limit on records to enrich"
    )
    cardinality: Literal["one_to_one", "many_to_one"] = Field(
        default="one_to_one",
        description="Cardinality of enricher data (one_to_one or many_to_one)",
    )
    aggregation: AggregationSchema | None = Field(
        default=None,
        description="Aggregation config for many_to_one enrichers",
    )

    @field_validator("join_keys")
    @classmethod
    def validate_join_keys_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure join_keys contains valid strings."""
        if not v:
            raise ValueError("join_keys cannot be empty")
        for key in v:
            if not key or not key.strip():
                raise ValueError("join_keys cannot contain empty strings")
        return v

    @model_validator(mode="after")
    def validate_aggregation_required(self) -> Self:
        """Ensure aggregation is provided when cardinality is many_to_one."""
        if self.cardinality == "many_to_one" and self.aggregation is None:
            raise ValueError(
                f"Enricher '{self.pipeline}' with cardinality=many_to_one "
                "requires aggregation config"
            )
        return self

    def to_domain(self) -> EnricherConfig:
        """Convert to immutable domain EnricherConfig."""
        return EnricherConfig(
            pipeline=self.pipeline,
            join_keys=tuple(self.join_keys),
            required=self.required,
            filter_condition=self.filter_condition,
            timeout_seconds=self.timeout_seconds,
            fallback_strategy=FallbackStrategy.from_string(self.fallback_strategy),
            silver_table=self.silver_table,
            limit=self.limit,
            cardinality=EnricherCardinality.from_string(self.cardinality),
            aggregation=self.aggregation.to_domain() if self.aggregation else None,
        )


class MergeOutputSchema(BaseModel):
    """Pydantic schema for merge output paths."""

    silver: str = Field(..., min_length=1, description="Path for merged Silver table")
    gold: str = Field(..., min_length=1, description="Path for merged Gold table")


class ColumnGroupSchema(BaseModel):
    """Pydantic schema for column group configuration.

    Defines how columns are grouped and ordered in merged output.
    """

    name: str = Field(..., min_length=1, description="Group name for logging")
    fields: list[str] = Field(
        default_factory=list, description="Explicit field names to include"
    )
    pattern: str | None = Field(
        default=None, description="Regex pattern to match field names"
    )
    provider_order: list[str] = Field(
        default_factory=lambda: [
            "chembl",
            "crossref",
            "openalex",
            "pubmed",
            "semanticscholar",
        ],
        description="Order of providers within this group",
    )

    @model_validator(mode="after")
    def validate_fields_or_pattern(self) -> ColumnGroupSchema:
        """Ensure at least one of fields or pattern is provided."""
        if not self.fields and not self.pattern:
            raise ValueError(
                f"Column group '{self.name}' must have either fields or pattern"
            )
        return self


class MergeSchema(BaseModel):
    """Pydantic schema for merge step configuration."""

    strategy: Literal["left_outer", "inner", "union"] = Field(
        default="left_outer", description="Join strategy for merging"
    )
    conflict_resolution: Literal[
        "seed_priority",
        "enricher_priority",
        "latest_timestamp",
        "explicit_rules",
        "coalesce",
    ] = Field(default="seed_priority", description="Strategy for field conflicts")
    field_priorities: dict[str, list[str]] = Field(
        default_factory=dict, description="Mapping of field to source priority list"
    )
    field_mappings: dict[str, str] = Field(
        default_factory=dict, description="Mapping to rename fields during merge"
    )
    output: MergeOutputSchema = Field(
        ..., description="Output paths for Silver and Gold tables"
    )
    preserve_all_sources: bool = Field(
        default=False,
        description="Keep all provider-qualified columns instead of coalescing",
    )
    column_groups: list[ColumnGroupSchema] = Field(
        default_factory=list,
        description="Column ordering by semantic groups",
    )
    column_groups_file: str | None = Field(
        default=None,
        description="Path to column group config file relative to composite config",
    )
    exclude_fields: list[str] = Field(
        default_factory=list,
        description="Columns to drop from merged output (supports glob patterns)",
    )

    @model_validator(mode="after")
    def validate_explicit_rules_requires_priorities(self) -> MergeSchema:
        """Ensure field_priorities is provided when using explicit_rules."""
        if self.conflict_resolution == "explicit_rules" and not self.field_priorities:
            raise ValueError(
                "field_priorities required when using explicit_rules conflict resolution"
            )
        return self

    def to_domain(self) -> MergeConfig:
        """Convert to immutable domain MergeConfig."""
        field_priorities_tuples = {
            k: tuple(v) for k, v in self.field_priorities.items()
        }
        # Convert column groups to domain objects
        column_groups_domain = tuple(
            ColumnGroupConfig(
                name=g.name,
                fields=tuple(g.fields),
                pattern=g.pattern,
                provider_order=tuple(g.provider_order),
            )
            for g in self.column_groups
        )
        return MergeConfig(
            strategy=MergeStrategy.from_string(self.strategy),
            conflict_resolution=ConflictResolution.from_string(
                self.conflict_resolution
            ),
            output_silver_path=self.output.silver,
            output_gold_path=self.output.gold,
            field_priorities=field_priorities_tuples,
            field_mappings=self.field_mappings,
            preserve_all_sources=self.preserve_all_sources,
            column_groups=column_groups_domain,
            exclude_fields=tuple(self.exclude_fields),
        )


class DQOverrideSchema(BaseModel):
    """Pydantic schema for per-enricher DQ threshold override."""

    soft_fail_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override soft threshold (0.0-1.0)"
    )
    hard_fail_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Override hard threshold (0.0-1.0)"
    )

    @model_validator(mode="after")
    def validate_threshold_order(self) -> DQOverrideSchema:
        """Ensure soft_fail_threshold < hard_fail_threshold when both set."""
        if (
            self.soft_fail_threshold is not None
            and self.hard_fail_threshold is not None
            and self.soft_fail_threshold >= self.hard_fail_threshold
        ):
            raise ValueError(
                "soft_fail_threshold must be less than hard_fail_threshold"
            )
        return self

    def to_domain(self) -> DQOverrideConfig:
        """Convert to immutable domain DQOverrideConfig."""
        return DQOverrideConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )


class CompositeDQSchema(BaseModel):
    """Pydantic schema for composite data quality configuration."""

    soft_fail_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Default soft threshold (0.0-1.0)"
    )
    hard_fail_threshold: float = Field(
        default=0.30, ge=0.0, le=1.0, description="Default hard threshold (0.0-1.0)"
    )
    enricher_overrides: dict[str, DQOverrideSchema] = Field(
        default_factory=dict, description="Per-enricher DQ threshold overrides"
    )
    required_fields: list[str] = Field(
        default_factory=list, description="Fields required in final Gold output"
    )

    @model_validator(mode="after")
    def validate_threshold_order(self) -> CompositeDQSchema:
        """Ensure soft_fail_threshold < hard_fail_threshold."""
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                f"soft_fail_threshold ({self.soft_fail_threshold}) must be "
                f"< hard_fail_threshold ({self.hard_fail_threshold})"
            )
        return self

    def to_domain(self) -> CompositeDQConfig:
        """Convert to immutable domain CompositeDQConfig."""
        overrides = {
            name: override.to_domain()
            for name, override in self.enricher_overrides.items()
        }
        return CompositeDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            enricher_overrides=overrides,
            required_fields=tuple(self.required_fields),
        )


class RetrySchema(BaseModel):
    """Pydantic schema for retry configuration."""

    max_attempts: int = Field(
        default=3, ge=0, description="Maximum retry attempts per enricher"
    )
    backoff_multiplier: float = Field(
        default=2.0, gt=0, description="Backoff multiplier for retries"
    )


class ExecutionSchema(BaseModel):
    """Pydantic schema for execution options."""

    max_concurrency: int = Field(
        default=4, gt=0, description="Maximum concurrent enrichers"
    )
    checkpoint_enabled: bool = Field(
        default=True, description="Enable checkpointing for resume"
    )
    retry: RetrySchema = Field(
        default_factory=RetrySchema, description="Retry configuration"
    )

    def to_domain(self) -> ExecutionConfig:
        """Convert to immutable domain ExecutionConfig."""
        return ExecutionConfig(
            max_concurrency=self.max_concurrency,
            checkpoint_enabled=self.checkpoint_enabled,
            retry_max_attempts=self.retry.max_attempts,
            retry_backoff_multiplier=self.retry.backoff_multiplier,
        )


class LineageSchema(BaseModel):
    """Pydantic schema for lineage tracking configuration."""

    track_field_sources: bool = Field(
        default=True, description="Track which source provided each field"
    )
    track_timestamps: bool = Field(
        default=True, description="Include enrichment timestamps"
    )
    track_status: bool = Field(
        default=True, description="Include per-record enrichment status"
    )
    provider_lookup_fields: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Per-provider mapping of lookup metadata field names",
    )
    track_source_for_fields: list[str] = Field(
        default_factory=list,
        description="Field names requiring source tracking for overlapping data",
    )

    def to_domain(self) -> LineageConfig:
        """Convert to immutable domain LineageConfig."""
        return LineageConfig(
            track_field_sources=self.track_field_sources,
            track_timestamps=self.track_timestamps,
            track_status=self.track_status,
            provider_lookup_fields=self.provider_lookup_fields,
            track_source_for_fields=tuple(self.track_source_for_fields),
        )


class FieldComparisonSpecSchema(BaseModel):
    """Pydantic schema for a single field comparison specification."""

    field: str = Field(..., min_length=1, description="Unified Silver column name")
    method: Literal["exact", "fuzzy", "numeric_tolerance", "skip"] = Field(
        default="exact", description="Comparison method"
    )
    threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Threshold for fuzzy/numeric"
    )

    def to_domain(self) -> FieldComparisonSpec:
        """Convert to domain FieldComparisonSpec."""
        return FieldComparisonSpec(
            field_name=self.field,
            method=ComparisonMethod(self.method),
            threshold=self.threshold,
        )


class EnricherFieldPairingSchema(BaseModel):
    """Pydantic schema for enricher field pairing."""

    enricher_pipeline: str = Field(
        ..., min_length=1, description="Enricher pipeline name"
    )
    fields: list[FieldComparisonSpecSchema] = Field(
        ..., min_length=1, description="Field comparison specs"
    )

    def to_domain(self) -> EnricherFieldPairing:
        """Convert to domain EnricherFieldPairing."""
        return EnricherFieldPairing(
            enricher_pipeline=self.enricher_pipeline,
            fields=tuple(f.to_domain() for f in self.fields),
        )


class CrossValidationSchema(BaseModel):
    """Pydantic schema for cross-validation configuration."""

    enabled: bool = Field(default=True, description="Enable cross-validation")
    warning_threshold: int = Field(
        default=1, ge=1, description="Mismatches to trigger WARNING"
    )
    error_threshold: int = Field(
        default=2, ge=2, description="Mismatches to trigger ENRICHER_ERROR"
    )
    quarantine_threshold: int = Field(
        default=2, ge=1, description="Enricher errors to quarantine seed"
    )
    fuzzy_threshold: float = Field(
        default=0.8, gt=0.0, le=1.0, description="Jaccard threshold for fuzzy"
    )
    numeric_tolerance: float = Field(
        default=0.10, gt=0.0, le=1.0, description="Relative tolerance for numeric"
    )
    enricher_pairings: list[EnricherFieldPairingSchema] = Field(
        default_factory=list, description="Per-enricher field pairings"
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        """Ensure warning_threshold < error_threshold."""
        if self.warning_threshold >= self.error_threshold:
            raise ValueError("warning_threshold must be < error_threshold")
        return self

    def to_domain(self) -> CrossValidationConfig:
        """Convert to domain CrossValidationConfig."""
        return CrossValidationConfig(
            enabled=self.enabled,
            warning_threshold=self.warning_threshold,
            error_threshold=self.error_threshold,
            quarantine_threshold=self.quarantine_threshold,
            fuzzy_threshold=self.fuzzy_threshold,
            numeric_tolerance=self.numeric_tolerance,
            enricher_pairings=tuple(p.to_domain() for p in self.enricher_pairings),
        )


class CompositeConfigSchema(BaseModel):
    """Pydantic schema for complete composite pipeline configuration.

    Validates the 'composite' section of YAML files and converts to
    domain CompositeConfig. Includes cross-field validation for join keys
    and enricher/dependency uniqueness.
    """

    name: str = Field(..., min_length=1, description="Composite pipeline name")
    version: str = Field(
        ..., min_length=1, description="Configuration version (semver)"
    )
    seed: SeedSchema = Field(..., description="Seed pipeline configuration")
    dependencies: list[DependencySchema] = Field(
        default_factory=list,
        description="List of dependency configurations (run after seed, before enrichers)",
    )
    enrichers: list[EnricherSchema] = Field(
        default_factory=list,
        description="List of enricher configurations (optional if dependencies provided)",
    )
    merge: MergeSchema = Field(..., description="Merge step configuration")
    dq_overrides: CompositeDQSchema = Field(
        default_factory=CompositeDQSchema,
        description="Data quality configuration",
    )
    execution: ExecutionSchema = Field(
        default_factory=ExecutionSchema, description="Execution options"
    )
    lineage: LineageSchema = Field(
        default_factory=LineageSchema, description="Lineage tracking configuration"
    )
    cross_validation: CrossValidationSchema = Field(
        default_factory=CrossValidationSchema,
        description="Cross-validation configuration for pre-merge checks",
    )

    @model_validator(mode="after")
    def validate_has_enrichers_or_dependencies(self) -> CompositeConfigSchema:
        """Validate that at least one enricher or dependency is defined."""
        if not self.enrichers and not self.dependencies:
            raise ValueError("At least one enricher or dependency must be defined")
        return self

    @model_validator(mode="after")
    def validate_enricher_join_keys(self) -> CompositeConfigSchema:
        """Validate that enricher join keys exist in seed output_keys."""
        if not self.enrichers:
            return self  # Skip if no enrichers
        seed_keys = set(self.seed.output_keys)
        for enricher in self.enrichers:
            for key in enricher.join_keys:
                if key not in seed_keys:
                    raise ValueError(
                        f"Enricher '{enricher.pipeline}' join_key '{key}' "
                        f"not found in seed output_keys: {self.seed.output_keys}"
                    )
        return self

    @model_validator(mode="after")
    def validate_dependency_join_keys(self) -> CompositeConfigSchema:
        """Validate that dependency join keys exist in seed output_keys.

        For chained dependencies (key_source != None and != "seed"),
        join_keys are taken from the key_source's Silver table,
        so they are NOT validated against seed output_keys.
        """
        seed_keys = set(self.seed.output_keys)
        for dep in self.dependencies:
            # Skip validation for chained dependencies
            if dep.key_source is not None and dep.key_source != "seed":
                continue
            for key in dep.join_keys:
                if key not in seed_keys:
                    raise ValueError(
                        f"Dependency '{dep.pipeline}' join_key '{key}' "
                        f"not found in seed output_keys: {self.seed.output_keys}"
                    )
        return self

    @model_validator(mode="after")
    def validate_unique_enricher_names(self) -> CompositeConfigSchema:
        """Validate that enricher pipeline names are unique."""
        if not self.enrichers:
            return self  # Skip if no enrichers
        names = [e.pipeline for e in self.enrichers]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate enricher pipelines: {duplicates}")
        return self

    @model_validator(mode="after")
    def validate_unique_dependency_names(self) -> CompositeConfigSchema:
        """Validate that dependency pipeline names are unique."""
        names = [d.pipeline for d in self.dependencies]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate dependency pipelines: {duplicates}")
        return self

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig."""
        return CompositeConfig(
            name=self.name,
            version=self.version,
            seed=self.seed.to_domain(),
            dependencies=tuple(d.to_domain() for d in self.dependencies),
            enrichers=tuple(e.to_domain() for e in self.enrichers),
            merge=self.merge.to_domain(),
            dq=self.dq_overrides.to_domain(),
            execution=self.execution.to_domain(),
            lineage=self.lineage.to_domain(),
            cross_validation=self.cross_validation.to_domain(),
        )


class CompositeConfigFileSchema(BaseModel):
    """Pydantic schema for complete composite configuration file.

    Validates the entire YAML file structure including schema_version
    and optional sections like gold_filters and maintenance.
    """

    schema_version: str = Field(
        default="2.0.0", description="Schema version for file format"
    )
    composite: CompositeConfigSchema = Field(
        ..., description="The composite pipeline configuration"
    )
    gold_filters: dict[str, Any] | None = Field(
        default=None, description="Optional gold layer filters"
    )
    maintenance: dict[str, Any] | None = Field(
        default=None, description="Optional maintenance configuration"
    )

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig."""
        return self.composite.to_domain()


class LegacyCompositeConfigSchema(CompositeConfigSchema):
    """Legacy schema for pre-v6 composite configs.

    Keeps `version` optional to support a deprecation window for historical
    YAML files that omitted `composite.version`.
    """

    version: str = Field(
        default="1.0.0", min_length=1, description="Configuration version (semver)"
    )


class LegacyCompositeConfigFileSchema(CompositeConfigFileSchema):
    """Legacy file schema where `composite.version` may be omitted."""

    composite: LegacyCompositeConfigSchema = Field(
        ..., description="The composite pipeline configuration"
    )


COMPOSITE_VERSION_DEPRECATION_TARGET = "6.2.0"


def validate_composite_config_payload(
    payload: dict[str, Any],
) -> CompositeConfigFileSchema:
    """Validate composite YAML payload with explicit legacy fallback.

    Runtime and generated JSON Schema both use :class:`CompositeConfigFileSchema`
    as the canonical contract. Legacy files (missing `composite.version`) are
    accepted only via an explicit compatibility path and emit a deprecation
    warning until BioETL v6.2.0.
    """

    try:
        result: CompositeConfigFileSchema = CompositeConfigFileSchema.model_validate(
            payload
        )
        return result
    except ValidationError:
        legacy_schema = LegacyCompositeConfigFileSchema.model_validate(payload)
        warnings.warn(
            "Composite config without 'composite.version' is deprecated and will "
            f"be removed in BioETL {COMPOSITE_VERSION_DEPRECATION_TARGET}. "
            "Add 'composite.version' explicitly.",
            DeprecationWarning,
            stacklevel=2,
        )
        normalized = legacy_schema.model_dump(mode="python")
        result = CompositeConfigFileSchema.model_validate(normalized)
        return result


__all__ = [
    "COMPOSITE_VERSION_DEPRECATION_TARGET",
    "AggregationFieldSchema",
    "AggregationSchema",
    "ColumnGroupSchema",
    "CompositeConfigFileSchema",
    "CompositeConfigSchema",
    "CompositeDQSchema",
    "CrossValidationSchema",
    "DQOverrideSchema",
    "DependencySchema",
    "EnricherFieldPairingSchema",
    "EnricherSchema",
    "ExecutionSchema",
    "FieldComparisonSpecSchema",
    "LineageSchema",
    "MergeOutputSchema",
    "MergeSchema",
    "RetrySchema",
    "SeedSchema",
    "validate_composite_config_payload",
]
