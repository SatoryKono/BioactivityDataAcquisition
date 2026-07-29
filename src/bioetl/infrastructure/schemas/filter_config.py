# mypy: disable-error-code="misc,untyped-decorator"
# MRO/override residual on mixin or client hierarchies.
"""Pydantic schemas for standalone filter configuration files.

Validates external filter configuration sections before converting
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
    >>> input_filter, silver_filters, gold_filters, extraction_params = config.to_domain()
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from bioetl.domain.filtering import (
    GoldFilterConfig,
    SilverFilterConfig,
)
from bioetl.domain.filtering import InputFilterConfig as DomainInputFilterConfig
from bioetl.domain.models.filter import ExtractionParams
from bioetl.infrastructure.schemas.base_schemas import (
    BaseGoldFiltersConfig,
    BaseInputFilterConfig,
)
from bioetl.infrastructure.schemas.source_profile_config import SourceProfileYamlConfig

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


class SilverFiltersFileConfig(BaseGoldFiltersConfig):
    """Silver filter configuration for structural Silver quality gates.

    Applied AFTER transformation but BEFORE writing to Silver layer.
    Semantic Gold-style keys are rejected at the schema boundary.

    Canonical Silver rules are limited to ``required_fields`` and
    ``exclude_if_present``. Do not add new semantic keys here.
    """

    @model_validator(mode="before")
    @classmethod
    def reject_semantic_silver_filters(cls, data: object) -> object:
        """Reject semantic keys even when this sub-schema is validated directly."""
        if isinstance(data, dict):
            from bioetl.domain.filtering.silver_config import (
                validate_structural_silver_filter_payload,
            )

            validate_structural_silver_filter_payload(data)
        return data

    def to_domain(self) -> SilverFilterConfig:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Convert to a structural-only domain SilverFilterConfig dataclass.

        Returns:
            SilverFilterConfig: Immutable domain filter configuration.
        """
        from bioetl.domain.filtering.silver_config import (
            build_silver_filter_config_for_compatibility,
        )

        return build_silver_filter_config_for_compatibility(super().to_domain())


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

    Represents filter configuration structure within entity config files.
    Supports hierarchical merge from defaults -> provider -> entity.

    Attributes:
        version: Schema version for compatibility checking.
        provider: Provider name (for provider/entity configs).
        entity: Entity name (for entity configs).
        input_filter: Input filtering configuration.
        silver_filters: Silver layer domain-level filter configuration.
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
    silver_filters: SilverFiltersFileConfig = Field(
        default_factory=SilverFiltersFileConfig,
        description="Silver layer domain-level filter configuration",
    )
    gold_filters: GoldFiltersFileConfig = Field(
        default_factory=GoldFiltersFileConfig,
        description="Gold layer filter configuration",
    )
    extraction_params: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Server-side API query parameters for Bronze extraction (ADR-028 §3)",
    )
    source_profile: SourceProfileYamlConfig = Field(
        default_factory=SourceProfileYamlConfig,
        description=(
            "Versioned source-profile metadata for extraction_params. "
            "This is provider request policy, not a Silver filter."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def reject_semantic_silver_filters(cls, data: object) -> object:
        """Reject semantic Silver rules before field validation."""
        if not isinstance(data, dict):
            return data
        from bioetl.domain.filtering.silver_config import (
            validate_no_semantic_silver_filter_payload,
        )

        return validate_no_semantic_silver_filter_payload(data)

    @field_validator("extraction_params")
    @classmethod
    def validate_extraction_params(
        cls,
        v: dict[str, str | int | bool],
    ) -> dict[str, str | int | bool]:
        """Validate extraction params keys and values.

        Args:
            v: Whether to v.

        Returns:
            Validated dict[str, str | int | bool].
        """
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

    @model_validator(mode="after")
    def validate_source_profile_hash(self) -> FilterConfigFile:
        """Validate declared source-profile hash against extraction params."""
        self.source_profile.assert_matches_extraction_params(self.extraction_params)
        return self

    def to_domain(
        self,
    ) -> tuple[
        DomainInputFilterConfig, SilverFilterConfig, GoldFilterConfig, ExtractionParams
    ]:
        """Convert to domain objects.

        Returns:
            Tuple of (InputFilterConfig, SilverFilterConfig, GoldFilterConfig,
            ExtractionParams).
        """
        return (
            self.input_filter.to_domain(),
            self.silver_filters.to_domain(),
            self.gold_filters.to_domain(),
            ExtractionParams(params=self.extraction_params),
        )


__all__ = [
    "FilterConfigFile",
    "GoldFiltersFileConfig",
    "InputFilterFileConfig",
    "SilverFiltersFileConfig",
    "SourceProfileYamlConfig",
]
