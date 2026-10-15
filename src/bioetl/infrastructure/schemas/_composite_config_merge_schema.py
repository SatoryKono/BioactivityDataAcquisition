# mypy: disable-error-code="misc,untyped-decorator"
"""Merge-related schemas for composite configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from bioetl.domain.composite import ColumnGroupConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

__all__ = [
    "ColumnGroupSchema",
    "MergeOutputSchema",
    "MergeSchema",
    "MergeSortBySchema",
    "TargetProteinClassificationProjectionSchema",
]


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
    """Pydantic schema for column group configuration."""

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


class TargetProteinClassificationProjectionSchema(BaseModel):
    """Typed projection for deterministic target protein classification aliases."""

    source_prefix: str = Field(
        default="chembl.target_protein_classification",
        description="Provider-qualified source prefix for projected classification fields",
    )
    include_protein_classifications: bool = Field(
        default=True,
        description="Whether to project the forensic protein_classifications payload",
    )
    levels: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5],
        description="Hierarchy levels to project into deterministic target fields",
    )

    @field_validator("levels")
    @classmethod
    def validate_levels(cls, value: list[int]) -> list[int]:
        normalized = sorted({int(level) for level in value})
        if not normalized or any(level <= 0 for level in normalized):
            raise ValueError("projection levels must contain positive integers")
        return normalized

    def expand_field_mappings(self) -> dict[str, str]:
        mappings: dict[str, str] = {}
        if self.include_protein_classifications:
            mappings[f"{self.source_prefix}.protein_classifications"] = (
                "protein_classifications"
            )
        for level in self.levels:
            for suffix in ("id", "name", "desc"):
                mappings[
                    (f"{self.source_prefix}.target_protein_class_{suffix}_L{level}")
                ] = f"target_protein_class_{suffix}_L{level}"
        return mappings


class MergeSchema(BaseModel):
    """Pydantic schema for merge step configuration."""

    model_config = ConfigDict(extra="forbid")

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
    normalization_compatibility_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Explicit justification map for intentional field-level normalization mismatches",
    )
    field_mappings: dict[str, str] = Field(
        default_factory=dict, description="Mapping to rename fields during merge"
    )
    target_protein_classification_projection: (
        TargetProteinClassificationProjectionSchema | None
    ) = Field(
        default=None,
        description="Typed projection contract for target protein classification aliases",
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
            key: tuple(value) for key, value in self.field_priorities.items()
        }
        field_mappings = dict(self.field_mappings)
        if self.target_protein_classification_projection is not None:
            field_mappings.update(
                self.target_protein_classification_projection.expand_field_mappings()
            )
        column_groups_domain = tuple(
            ColumnGroupConfig(
                name=group.name,
                fields=tuple(group.fields),
                pattern=group.pattern,
                provider_order=tuple(group.provider_order),
            )
            for group in self.column_groups
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
            normalization_compatibility_overrides=self.normalization_compatibility_overrides,
            field_mappings=field_mappings,
            preserve_all_sources=self.preserve_all_sources,
            column_groups=column_groups_domain,
            exclude_fields=tuple(self.exclude_fields),
        )
