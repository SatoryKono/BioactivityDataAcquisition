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
    >>> input_filter, gold_filters, extraction_params = config.to_domain()
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from bioetl.domain.filtering import GoldFilterConfig
from bioetl.domain.filtering import (
    InputFilterConfig as DomainInputFilterConfig,
)
from bioetl.domain.models.filter import ExtractionParams
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
# These are type aliases pointing to base classes for API consistency.
# New code should use the classes from base_schemas directly.

# Re-export base classes with filter_config-specific names
FilterColumnSchema = BaseFilterColumnSchema
GoldRangeFilterConfig = BaseGoldRangeFilterConfig
GoldListLengthFilterConfig = BaseGoldListLengthFilterConfig
GoldListContainsFilterConfig = BaseGoldListContainsFilterConfig
GoldColumnFilterConfig = BaseGoldColumnFilterConfig


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
    extraction_params: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Server-side API query parameters for Bronze extraction (ADR-028 §3)",
    )

    @field_validator("extraction_params")  # type: ignore[untyped-decorator]
    @classmethod
    def validate_extraction_params(
        cls,
        v: dict[str, str | int | bool],
    ) -> dict[str, str | int | bool]:
        """Validate extraction params keys and values."""
        for key, value in v.items():
            if not key or not isinstance(key, str):
                raise ValueError(
                    f"Extraction param key must be non-empty string, got: {key!r}"
                )
            if not isinstance(value, (str, int, bool)):
                raise ValueError(
                    f"Extraction param '{key}' value must be str|int|bool, "
                    f"got {type(value).__name__}: {value!r}"
                )
        return v

    def to_domain(
        self,
    ) -> tuple[DomainInputFilterConfig, GoldFilterConfig, ExtractionParams]:
        """Convert to domain objects.

        Returns:
            Tuple of (InputFilterConfig, GoldFilterConfig, ExtractionParams).
        """
        return (
            self.input_filter.to_domain(),
            self.gold_filters.to_domain(),
            ExtractionParams(params=self.extraction_params),
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
