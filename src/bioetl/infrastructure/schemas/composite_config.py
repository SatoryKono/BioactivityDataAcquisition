"""Pydantic schemas for composite pipeline configuration files.

Validates composite pipeline YAML files (configs/composites/*.yaml)
before converting to domain objects. Implements ADR-026 Composite Pipeline Pattern.

Usage:
    >>> schema = CompositeConfigFileSchema.model_validate(yaml_data)
    >>> domain_config = schema.to_domain()
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    CompositeConfig,
    MergeConfig,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    MergeStrategy,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.schemas.composite_config_base import (
    AggregationFieldSchema,
    AggregationSchema,
    DependencySchema,
    EnricherSchema,
    SeedSchema,
)
from bioetl.infrastructure.schemas.composite_validation import (
    CompositeDQSchema,
    CrossValidationSchema,
    DQOverrideSchema,
    EnricherFieldPairingSchema,
    ExecutionSchema,
    FieldComparisonSpecSchema,
    LineageSchema,
    RetrySchema,
)


class MergeOutputSchema(BaseModel):
    """Pydantic schema for merge output paths."""

    silver: str = Field(..., min_length=1, description="Path for merged Silver table")
    gold: str = Field(..., min_length=1, description="Path for merged Gold table")


class MergeSortBySchema(BaseModel):
    """Deterministic sort policy for merged Silver/Gold outputs."""

    silver: list[str] = Field(
        ..., min_length=1, description="Sort columns for merged Silver output"
    )
    gold: list[str] = Field(
        ..., min_length=1, description="Sort columns for merged Gold output"
    )

    @field_validator("silver", "gold")
    @classmethod
    def validate_non_empty_unique_columns(cls, value: list[str]) -> list[str]:
        """Normalize and validate deterministic sort columns."""
        normalized = [column.strip() for column in value]
        if any(not column for column in normalized):
            raise ValueError("sort_by must not contain empty column names")
        if len(normalized) != len(set(normalized)):
            raise ValueError("sort_by must not contain duplicate columns")
        return normalized


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
        """Ensure at least one of fields or pattern is provided.

        Returns:
            Validated ColumnGroupSchema.
        """
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
    sort_by: MergeSortBySchema = Field(
        ..., description="Deterministic row ordering policy for merged outputs"
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
        """Ensure field_priorities is provided when using explicit_rules.

        Returns:
            Validated MergeSchema.
        """
        if self.conflict_resolution == "explicit_rules" and not self.field_priorities:
            raise ValueError(
                "field_priorities required when using explicit_rules conflict resolution"
            )
        return self

    def to_domain(self) -> MergeConfig:
        """Convert to immutable domain MergeConfig.

        Returns:
            The MergeConfig result.
        """
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
            sort_by_silver=tuple(self.sort_by.silver),
            sort_by_gold=tuple(self.sort_by.gold),
            field_priorities=field_priorities_tuples,
            field_mappings=self.field_mappings,
            preserve_all_sources=self.preserve_all_sources,
            column_groups=column_groups_domain,
            exclude_fields=tuple(self.exclude_fields),
        )


class CompositeConfigSchema(BaseModel):
    """Pydantic schema for complete composite pipeline configuration.

    Validates structural/types contract for the 'composite' YAML section and
    converts to domain CompositeConfig.

    Business invariants (join-key compatibility, uniqueness, etc.) are owned by
    the domain layer and enforced via delegated validation.
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
    def validate_domain_invariants(self) -> Self:
        """Delegate business invariant checks to domain CompositeConfig.

        Keeps infrastructure schema focused on structural/type validation and
        conversion while preserving ValidationError UX at schema boundary.
        """
        try:
            self.to_domain()
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig.

        Returns:
            The CompositeConfig result.
        """
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
    gold_filters: JsonDict | None = (  # Any: YAML config has heterogeneous values
        Field(  # Any: YAML config has heterogeneous values
            default=None, description="Optional gold layer filters"
        )
    )
    maintenance: JsonDict | None = (  # Any: YAML config has heterogeneous values
        Field(  # Any: YAML config has heterogeneous values
            default=None, description="Optional maintenance configuration"
        )
    )

    def to_domain(self) -> CompositeConfig:
        """Convert to immutable domain CompositeConfig.

        Returns:
            The CompositeConfig result.
        """
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
    payload: JsonDict,  # Any: YAML config has heterogeneous values
) -> CompositeConfigFileSchema:
    """Validate composite YAML payload with explicit legacy fallback.

    Runtime and generated JSON Schema both use :class:`CompositeConfigFileSchema`
    as the canonical contract. Legacy files (missing `composite.version`) are
    accepted only via an explicit compatibility path.

    Args:
        payload: Data payload.

    Returns:
        Validated CompositeConfigFileSchema.
    """

    try:
        result: CompositeConfigFileSchema = CompositeConfigFileSchema.model_validate(
            payload
        )
        return result
    except ValidationError:
        legacy_schema = LegacyCompositeConfigFileSchema.model_validate(payload)
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
    "MergeSortBySchema",
    "RetrySchema",
    "SeedSchema",
    "validate_composite_config_payload",
]
