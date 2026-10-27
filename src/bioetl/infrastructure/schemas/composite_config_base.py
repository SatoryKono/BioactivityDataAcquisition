# mypy: disable-error-code="misc,untyped-decorator"
"""Shared seed/dependency/enricher schemas for composite config."""

from __future__ import annotations

__all__ = [
    "AggregationFieldSchema",
    "AggregationSchema",
    "DependencySchema",
    "EnricherSchema",
    "SeedSchema",
]


from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from bioetl.domain.composite import (
    DependencyConfig,
    EnricherConfig,
    SeedConfig,
)
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.strategy import FallbackStrategy


class AggregationFieldSchema(BaseModel):
    """Pydantic schema for aggregation field specification."""

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

        Returns:
            AggregationFieldSpec instance with source field, aggregation function, and filter.
        """
        return AggregationFieldSpec(
            source_field=self.source,
            agg_function=AggregationFunction.from_string(self.agg),
            filter_condition=self.filter,
            output_field=output_field,
        )


class AggregationSchema(BaseModel):
    """Pydantic schema for 1:M enricher aggregation config."""

    group_by: str = Field(..., min_length=1, description="Join key to group by")
    order_by: list[str] = Field(
        default_factory=list,
        description="Canonical ordering columns used before deterministic aggregation",
    )
    fields: dict[str, AggregationFieldSchema] = Field(
        ..., min_length=1, description="Map of output_field -> aggregation spec"
    )

    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, value: list[str]) -> list[str]:
        """Normalize and reject empty/duplicate deterministic ordering columns."""
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("aggregation.order_by cannot contain empty column names")
        if len(set(normalized)) != len(normalized):
            raise ValueError("aggregation.order_by cannot contain duplicate columns")
        return normalized

    def to_domain(self) -> AggregationConfig:
        """Convert to domain AggregationConfig.

        Returns:
            AggregationConfig instance with group_by field and aggregation field specs.
        """
        return AggregationConfig(
            group_by=self.group_by,
            order_by=tuple(self.order_by),
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
    def validate_output_keys_not_empty(cls, value: list[str]) -> list[str]:
        """Ensure output_keys contains valid strings."""
        if not value:
            raise ValueError("output_keys cannot be empty")
        for key in value:
            if not key or not key.strip():
                raise ValueError("output_keys cannot contain empty strings")
        return value

    def to_domain(self) -> SeedConfig:
        """Convert to immutable domain SeedConfig.

        Returns:
            SeedConfig instance with pipeline name, output keys, silver table, and limit.
        """
        return SeedConfig(
            pipeline=self.pipeline,
            output_keys=tuple(self.output_keys),
            silver_table=self.silver_table,
            limit=self.limit,
        )


class DependencySchema(BaseModel):
    """Pydantic schema for dependency pipeline configuration."""

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
    def validate_join_keys_not_empty(cls, value: list[str]) -> list[str]:
        """Ensure join_keys contains valid strings."""
        if not value:
            raise ValueError("join_keys cannot be empty")
        for key in value:
            if not key or not key.strip():
                raise ValueError("join_keys cannot contain empty strings")
        return value

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
        """Convert to immutable domain DependencyConfig.

        Returns:
            DependencyConfig instance with pipeline, join keys, timeout, and filter settings.
        """
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
    def validate_join_keys_not_empty(cls, value: list[str]) -> list[str]:
        """Ensure join_keys contains valid strings."""
        if not value:
            raise ValueError("join_keys cannot be empty")
        for key in value:
            if not key or not key.strip():
                raise ValueError("join_keys cannot contain empty strings")
        return value

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
        """Convert to immutable domain EnricherConfig.

        Returns:
            EnricherConfig instance with pipeline, join keys, cardinality, and aggregation settings.
        """
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
