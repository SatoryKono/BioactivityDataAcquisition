"""Pydantic schemas for standalone filter configuration files.

Validates external YAML files (configs/filter/*.yaml) before converting
to domain objects. Supports hierarchical merge of configurations.

This module uses base classes from `base_schemas` to eliminate duplication
with `pipeline_config.py`.

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

from pydantic import BaseModel, Field

from bioetl.domain.filtering import GoldFilterConfig
from bioetl.domain.filtering import (
    InputFilterConfig as DomainInputFilterConfig,
)
from bioetl.infrastructure.schemas.base_schemas import (
    BaseFilterColumnSchema,
    BaseGoldColumnFilterConfig,
    BaseGoldFiltersConfig,
    BaseGoldListContainsFilterConfig,
    BaseGoldListLengthFilterConfig,
    BaseGoldRangeFilterConfig,
    BaseInputFilterConfig,
)


# =============================================================================
# Type Aliases for Backward Compatibility
# =============================================================================
# These are re-exported from pipeline_config.py for consistency
# New code should use the classes from base_schemas directly


class FilterColumnSchema(BaseFilterColumnSchema):
    """Schema for a single filter column configuration.

    Inherits from BaseFilterColumnSchema for consistency with pipeline_config.
    """

    pass


class GoldRangeFilterConfig(BaseGoldRangeFilterConfig):
    """Schema for range filters in YAML.

    Inherits from BaseGoldRangeFilterConfig for consistency with pipeline_config.
    """

    pass


class GoldListLengthFilterConfig(BaseGoldListLengthFilterConfig):
    """Schema for list length filters in YAML.

    Inherits from BaseGoldListLengthFilterConfig for consistency with pipeline_config.
    """

    pass


class GoldListContainsFilterConfig(BaseGoldListContainsFilterConfig):
    """Schema for list contains filters in YAML.

    Inherits from BaseGoldListContainsFilterConfig for consistency with pipeline_config.
    """

    pass


class GoldColumnFilterConfig(BaseGoldColumnFilterConfig):
    """Column filter config with operator support.

    Inherits from BaseGoldColumnFilterConfig for consistency with pipeline_config.
    """

    pass


# =============================================================================
# Filter Configuration File Schemas
# =============================================================================


class InputFilterFileConfig(BaseInputFilterConfig):
    """Input filter configuration for standalone filter files.

    Inherits from BaseInputFilterConfig to eliminate duplication with
    pipeline_config.InputFilterConfig.

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

    # Override columns to use local FilterColumnSchema for proper serialization
    columns: list[FilterColumnSchema] | None = Field(
        default=None,
        description="List of column configurations for multi-column filtering",
    )

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert to domain InputFilterConfig dataclass.

        Returns:
            DomainInputFilterConfig: Immutable domain configuration.
        """
        return super().to_domain()


class GoldFiltersFileConfig(BaseGoldFiltersConfig):
    """Gold filter configuration for standalone filter files.

    Inherits from BaseGoldFiltersConfig to eliminate duplication with
    pipeline_config.GoldFiltersConfig.

    Supports two formats for columns:
    - Legacy format: {"column_name": ["value1", "value2"]} (IN operator)
    - New format: {"column_name": {"operator": "in", "values": ["value1", "value2"]}}

    Attributes:
        columns: Column value filters with operator support.
        ranges: Numeric range filters.
        list_lengths: List length filters.
        list_contains: List contains filters.
        required_fields: Required non-null fields.
        exclude_if_present: Exclude if field has value.
    """

    # Override with local type aliases for proper serialization
    columns: dict[str, list[str] | GoldColumnFilterConfig] = Field(default_factory=dict)
    ranges: dict[str, GoldRangeFilterConfig] = Field(default_factory=dict)
    list_lengths: dict[str, GoldListLengthFilterConfig] = Field(default_factory=dict)
    list_contains: dict[str, GoldListContainsFilterConfig] = Field(default_factory=dict)

    def to_domain(self) -> GoldFilterConfig:
        """Convert to domain GoldFilterConfig dataclass.

        Returns:
            GoldFilterConfig: Immutable domain configuration.
        """
        return super().to_domain()


class FilterConfigFile(BaseModel):
    """Complete filter configuration file schema.

    Represents structure of configs/filter/*.yaml files.
    Supports hierarchical merge from defaults -> provider -> entity.

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
    "FilterColumnSchema",
    "FilterConfigFile",
    "GoldColumnFilterConfig",
    "GoldFiltersFileConfig",
    "GoldListContainsFilterConfig",
    "GoldListLengthFilterConfig",
    "GoldRangeFilterConfig",
    "InputFilterFileConfig",
]
