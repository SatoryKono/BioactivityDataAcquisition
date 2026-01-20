"""Pydantic schemas for standalone filter configuration files.

Validates external YAML files (configs/filter/*.yaml) before converting
to domain objects. Supports hierarchical merge of configurations.

Implements ADR-028: Filter Rules Externalization.

Structure:
    InputFilterFileConfig: Input filter configuration for API filtering.
    GoldFiltersFileConfig: Gold layer filter configuration.
    FilterConfigFile: Complete filter configuration file schema.

Usage:
    >>> from bioetl.infrastructure.schemas.filter_config import FilterConfigFile
    >>> config = FilterConfigFile.model_validate(yaml_data)
    >>> input_filter, gold_filters = config.to_domain()
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from bioetl.domain.filtering import (
    GoldColumnFilter,
    GoldFilterConfig,
    GoldListContainsFilter,
    GoldListLengthFilter,
    GoldRangeFilter,
)
from bioetl.domain.filtering import (
    InputFilterConfig as DomainInputFilterConfig,
)
from bioetl.domain.filtering.input_config import FilterColumn as DomainFilterColumn
from bioetl.infrastructure.schemas.pipeline_config import (
    FilterColumnSchema,
    GoldListContainsFilterConfig,
    GoldListLengthFilterConfig,
    GoldRangeFilterConfig,
)


class InputFilterFileConfig(BaseModel):
    """Input filter configuration for standalone filter files.

    Supports both single-column and multi-column filtering modes.

    Attributes:
        enabled: Whether input filtering is enabled.
        source_path: Path to CSV file with filter IDs.
        column_name: CSV column with primary IDs (single-column mode).
        filter_field: API field to filter by (single-column mode).
        columns: List of columns for multi-column mode.
        batch_size: IDs per API request.
        fallback_column: Fallback search field (e.g., title).
    """

    enabled: bool = False
    source_path: str | None = Field(
        default=None,
        description="Path to CSV file with filter IDs",
    )
    column_name: str | None = Field(
        default=None,
        description="Column name in CSV containing filter IDs (single-column mode)",
    )
    filter_field: str | None = Field(
        default=None,
        description="API field name to filter by (single-column mode)",
    )
    columns: list[FilterColumnSchema] | None = Field(
        default=None,
        description="List of column configurations for multi-column filtering",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of IDs per API request",
    )
    fallback_column: str | None = Field(
        default=None,
        description="Column name for fallback search when primary lookup fails",
    )

    @model_validator(mode="after")
    def validate_column_config(self) -> InputFilterFileConfig:
        """Validate that either columns or column_name/filter_field is provided."""
        if not self.enabled:
            return self
        if self.columns:
            return self
        if self.column_name and self.filter_field:
            return self
        raise ValueError(
            "Either 'columns' list or both 'column_name' and 'filter_field' "
            "must be provided when filter is enabled"
        )

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert to domain InputFilterConfig dataclass.

        Returns:
            DomainInputFilterConfig: Immutable domain configuration.
        """
        domain_columns: tuple[DomainFilterColumn, ...] = ()
        if self.columns:
            domain_columns = tuple(
                DomainFilterColumn(
                    column_name=col.column_name,
                    filter_field=col.filter_field,
                )
                for col in self.columns
            )

        return DomainInputFilterConfig(
            enabled=self.enabled,
            source_path=self.source_path,
            column_name=self.column_name if self.enabled and not self.columns else None,
            filter_field=(
                self.filter_field if self.enabled and not self.columns else None
            ),
            columns=domain_columns,
            batch_size=self.batch_size,
            fallback_column=self.fallback_column,
        )


class GoldFiltersFileConfig(BaseModel):
    """Gold filter configuration for standalone filter files.

    Attributes:
        columns: Column value filters (inclusion lists).
        ranges: Numeric range filters.
        list_lengths: List length filters.
        list_contains: List contains filters.
        required_fields: Required non-null fields.
        exclude_if_present: Exclude if field has value.
    """

    columns: dict[str, list[str]] = Field(default_factory=dict)
    ranges: dict[str, GoldRangeFilterConfig] = Field(default_factory=dict)
    list_lengths: dict[str, GoldListLengthFilterConfig] = Field(default_factory=dict)
    list_contains: dict[str, GoldListContainsFilterConfig] = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)
    exclude_if_present: list[str] = Field(default_factory=list)

    def to_domain(self) -> GoldFilterConfig:
        """Convert to domain GoldFilterConfig dataclass.

        Returns:
            GoldFilterConfig: Immutable domain configuration.
        """
        return GoldFilterConfig(
            column_filters=tuple(
                GoldColumnFilter(column=col, values=frozenset(vals))
                for col, vals in self.columns.items()
            ),
            range_filters=tuple(
                GoldRangeFilter(
                    column=col,
                    min_value=r.min,
                    max_value=r.max,
                    include_min=r.include_min,
                    include_max=r.include_max,
                )
                for col, r in self.ranges.items()
            ),
            list_length_filters=tuple(
                GoldListLengthFilter(column=col, min_length=r.min, max_length=r.max)
                for col, r in self.list_lengths.items()
            ),
            list_contains_filters=tuple(
                GoldListContainsFilter(
                    column=col, values=frozenset(r.values), mode=r.mode
                )
                for col, r in self.list_contains.items()
            ),
            required_fields=tuple(self.required_fields),
            exclude_if_present=tuple(self.exclude_if_present),
        )


class FilterConfigFile(BaseModel):
    """Complete filter configuration file schema.

    Represents structure of configs/filter/*.yaml files.
    Supports hierarchical merge from defaults → provider → entity.

    Attributes:
        version: Schema version for compatibility checking.
        provider: Provider name (for provider/entity configs).
        entity: Entity name (for entity configs).
        input_filter: Input filtering configuration.
        gold_filters: Gold layer filter configuration.
    """

    version: str = Field(
        default="1.0.0",
        description="Schema version for compatibility checking",
    )
    provider: str | None = Field(
        default=None,
        description="Provider name (for provider/entity configs)",
    )
    entity: str | None = Field(
        default=None,
        description="Entity name (for entity configs)",
    )
    input_filter: InputFilterFileConfig = Field(
        default_factory=InputFilterFileConfig,
        description="Input filtering configuration",
    )
    gold_filters: GoldFiltersFileConfig = Field(
        default_factory=GoldFiltersFileConfig,
        description="Gold layer filter configuration",
    )

    def to_domain(self) -> tuple[DomainInputFilterConfig, GoldFilterConfig]:
        """Convert to domain objects.

        Returns:
            Tuple of (InputFilterConfig, GoldFilterConfig).
        """
        return (
            self.input_filter.to_domain(),
            self.gold_filters.to_domain(),
        )


__all__ = [
    "FilterConfigFile",
    "GoldFiltersFileConfig",
    "InputFilterFileConfig",
]
