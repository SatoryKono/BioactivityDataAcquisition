# mypy: disable-error-code="misc,untyped-decorator"
"""Shared base schemas for input filtering and gold filtering configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.filtering.input_config import (
        InputFilterConfig as DomainInputFilterConfig,
    )


type FilterScalar = str | int | bool


class BaseFilterColumnSchema(BaseModel):
    """Base class for filter column configuration."""

    model_config = ConfigDict(extra="ignore")

    column_name: str = Field(description="Column name in CSV containing filter IDs")
    filter_field: str = Field(description="API field name to filter by")


class BaseInputFilterConfig(BaseModel):
    """Base class for input filter configuration."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False, description="Whether input filtering is enabled"
    )
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
    columns: list[BaseFilterColumnSchema] | None = Field(
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
    def validate_column_config(self) -> BaseInputFilterConfig:
        """Validate that either columns or column_name/filter_field is provided."""
        if (
            self.enabled
            and not self.columns
            and not (self.column_name and self.filter_field)
        ):
            raise ValueError(
                "Either 'columns' list or both 'column_name' and 'filter_field' "
                "must be provided when filter is enabled"
            )
        return self

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert to domain InputFilterConfig dataclass."""
        from bioetl.domain.filtering.input_config import (
            FilterColumn as DomainFilterColumn,
        )
        from bioetl.domain.filtering.input_config import (
            InputFilterConfig as DomainInputFilterConfigImpl,
        )

        domain_columns: tuple[DomainFilterColumn, ...] = ()
        if self.columns:
            domain_columns = tuple(
                DomainFilterColumn(
                    column_name=col.column_name,
                    filter_field=col.filter_field,
                )
                for col in self.columns
            )

        return DomainInputFilterConfigImpl(
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


class BaseGoldRangeFilterConfig(BaseModel):
    """Base class for Gold range filter configuration."""

    model_config = ConfigDict(extra="ignore")

    min: float | None = Field(default=None, description="Minimum value")
    max: float | None = Field(default=None, description="Maximum value")
    include_min: bool = Field(default=True, description="Whether to include minimum")
    include_max: bool = Field(default=True, description="Whether to include maximum")


class BaseGoldListLengthFilterConfig(BaseModel):
    """Base class for Gold list length filter configuration."""

    model_config = ConfigDict(extra="ignore")

    min: int | None = Field(default=None, description="Minimum list length")
    max: int | None = Field(default=None, description="Maximum list length")


class BaseGoldListContainsFilterConfig(BaseModel):
    """Base class for Gold list contains filter configuration."""

    model_config = ConfigDict(extra="ignore")

    values: list[str] = Field(description="Values that must be present in the list")
    mode: Literal["all", "any"] = Field(
        default="all",
        description="Match mode ('all' or 'any')",
    )


class BaseGoldColumnFilterConfig(BaseModel):
    """Base class for Gold column filter configuration."""

    model_config = ConfigDict(extra="ignore")

    operator: Literal[
        "in", "not_in", "is_null", "is_not_null", "is_empty", "is_not_empty"
    ] = Field(default="in", description="Filter operator")
    values: list[FilterScalar] | None = Field(
        default=None,
        description="Allowed/excluded values (for in/not_in operators)",
    )

    @model_validator(mode="after")
    def validate_operator_values(self) -> BaseGoldColumnFilterConfig:
        """Validate that values are provided only when needed."""
        if self.operator in ("in", "not_in") and not self.values:
            raise ValueError(f"values required for operator '{self.operator}'")
        if (
            self.operator in ("is_null", "is_not_null", "is_empty", "is_not_empty")
            and self.values is not None
        ):
            raise ValueError(f"values must be None for operator '{self.operator}'")
        return self


class BaseGoldFiltersConfig(BaseModel):
    """Base class for Gold filters configuration."""

    model_config = ConfigDict(extra="ignore")

    columns: dict[str, list[FilterScalar] | BaseGoldColumnFilterConfig] = Field(
        default_factory=dict,
        description="Column value filters",
    )
    ranges: dict[str, BaseGoldRangeFilterConfig] = Field(
        default_factory=dict,
        description="Numeric range filters",
    )
    list_lengths: dict[str, BaseGoldListLengthFilterConfig] = Field(
        default_factory=dict,
        description="List length filters",
    )
    list_contains: dict[str, BaseGoldListContainsFilterConfig] = Field(
        default_factory=dict,
        description="List contains filters",
    )
    required_fields: list[str] = Field(
        default_factory=list,
        description="Required non-null fields",
    )
    exclude_if_present: list[str] = Field(
        default_factory=list,
        description="Exclude if field has value",
    )

    def to_domain(self) -> GoldFilterConfig:
        """Convert to domain GoldFilterConfig dataclass."""
        from bioetl.domain.filtering import (
            FilterOperator,
            GoldColumnFilter,
            GoldFilterConfig,
            GoldListContainsFilter,
            GoldListLengthFilter,
            GoldRangeFilter,
        )

        column_filters: list[GoldColumnFilter] = []
        for col, cfg in self.columns.items():
            if isinstance(cfg, list):
                column_filters.append(
                    GoldColumnFilter(
                        column=col,
                        operator=FilterOperator.IN,
                        values=frozenset(cfg),
                    )
                )
                continue
            column_filters.append(
                GoldColumnFilter(
                    column=col,
                    operator=FilterOperator(cfg.operator),
                    values=frozenset(cfg.values) if cfg.values else None,
                )
            )

        return GoldFilterConfig(
            column_filters=tuple(column_filters),
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


__all__ = [
    "BaseFilterColumnSchema",
    "BaseGoldColumnFilterConfig",
    "BaseGoldFiltersConfig",
    "BaseGoldListContainsFilterConfig",
    "BaseGoldListLengthFilterConfig",
    "BaseGoldRangeFilterConfig",
    "BaseInputFilterConfig",
]
