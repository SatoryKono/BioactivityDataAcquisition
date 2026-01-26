"""Base configuration schemas for shared configuration components.

This module provides base Pydantic models for configuration components that are
used across multiple schema files. It eliminates duplication by defining common
fields and validation logic in one place.

Design Principles:
    - Single Source of Truth: Each configuration field is defined once
    - DRY: No duplicate field definitions across schema files
    - Extensibility: Base classes can be extended for specific use cases
    - Domain Conversion: Each model has `to_domain()` for converting to domain objects

Usage:
    Other schema files should import and inherit from these base classes:

    >>> from bioetl.infrastructure.schemas.base_schemas import BaseCircuitBreakerConfig
    >>> class CircuitBreakerConfig(BaseCircuitBreakerConfig):
    ...     # Add additional fields or override methods if needed
    ...     pass

Hierarchy:
    base_schemas.py (this file)
    ├── pipeline_config.py (imports base classes)
    ├── source_config.py (imports base classes)
    ├── filter_config.py (imports base classes)
    └── common_config.py (re-exports for backward compatibility)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.configs.base import (
    BaseClientConfig as DomainBaseClientConfig,
)
from bioetl.domain.configs.base import (
    RateLimitConfig,
)
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.filtering.input_config import (
        FilterColumn as DomainFilterColumn,
    )
    from bioetl.domain.filtering.input_config import (
        InputFilterConfig as DomainInputFilterConfig,
    )


# =============================================================================
# DQ Configuration Base Classes
# =============================================================================


class BaseDQThresholds(BaseModel):
    """Base class for DQ threshold configuration.

    Provides common threshold fields and validation logic for both
    inline DQ configs and standalone DQ config files.

    Attributes:
        soft_fail_threshold: Warning threshold (0.0-1.0). Default: 0.05 (5%).
        hard_fail_threshold: Failure threshold (0.0-1.0). Default: 0.20 (20%).
    """

    model_config = ConfigDict(extra="ignore")

    soft_fail_threshold: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Warning threshold (0.0-1.0). Default: 0.05 (5%)",
    )
    hard_fail_threshold: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Failure threshold (0.0-1.0). Default: 0.20 (20%)",
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> BaseDQThresholds:
        """Validate that soft threshold is less than hard threshold.

        Delegates to domain DQConfig for threshold validation per RULES.md §4.1.
        Raises ValueError if soft_fail_threshold >= hard_fail_threshold.

        Returns:
            Self after validation.

        Raises:
            ValueError: If threshold invariant is violated.
        """
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self


class BaseDQConfig(BaseDQThresholds):
    """Base class for DQ configuration.

    Extends BaseDQThresholds with strict_validation flag.
    Used as base for both simple and extended DQ configs.

    Attributes:
        strict_validation: If True, apply stricter validation rules.
    """

    strict_validation: bool = Field(
        default=False,
        description="Apply stricter validation rules (feature flag)",
    )

    def to_domain(self) -> DomainDQConfig:
        """Convert to domain DQConfig dataclass.

        Returns:
            DomainDQConfig: Immutable domain configuration.
        """
        return DomainDQConfig(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
            strict_validation=self.strict_validation,
        )


# =============================================================================
# Resilience Configuration Base Classes
# =============================================================================


class BaseCircuitBreakerConfig(BaseModel):
    """Base class for Circuit Breaker configuration.

    Provides common circuit breaker fields for both pipeline and source configs.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit.
        recovery_timeout: Time in seconds before attempting recovery.
    """

    model_config = ConfigDict(extra="ignore")

    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of consecutive failures before opening circuit",
    )
    recovery_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Time in seconds before attempting recovery",
    )

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass.

        Returns:
            DomainCircuitBreakerConfig: Immutable domain configuration.
        """
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class BaseRateLimitConfig(BaseModel):
    """Base class for Rate Limit configuration.

    Provides common rate limit fields for both pipeline and source configs.

    Attributes:
        requests_per_second: Maximum requests per second.
        burst: Maximum burst capacity (token bucket).
    """

    model_config = ConfigDict(extra="ignore")

    requests_per_second: float = Field(
        default=5.0,
        ge=0.1,
        le=100.0,
        description="Maximum requests per second",
    )
    burst: int = Field(
        default=10,
        ge=1,
        le=200,
        description="Maximum burst capacity (token bucket)",
    )


class BaseClientConfig(BaseModel):
    """Base class for HTTP Client configuration.

    Provides common HTTP client fields for both pipeline and source configs.

    Attributes:
        timeout_sec: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
    """

    model_config = ConfigDict(extra="ignore")

    timeout_sec: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )


# =============================================================================
# API Configuration Base Classes
# =============================================================================


class BaseApiConfig(BaseModel):
    """Base class for API connection configuration.

    Provides common API connection fields.

    Attributes:
        base_url: Base URL for the API.
        rate_limit: Rate limit in requests per second.
        timeout: Request timeout in seconds.
    """

    model_config = ConfigDict(extra="ignore")

    base_url: str | None = Field(
        default=None,
        description="Base URL for the API",
    )
    rate_limit: float | None = Field(
        default=None,
        description="Rate limit in requests per second",
    )
    timeout: int | None = Field(
        default=None,
        description="Request timeout in seconds",
    )

    def to_domain(self) -> DomainBaseClientConfig:
        """Convert to domain BaseClientConfig dataclass.

        Creates domain configuration for API client with defaults:
        - timeout: 30 seconds if not specified
        - rate_limit: 5.0 requests/second if not specified

        Returns:
            Domain-layer BaseClientConfig for HTTP client initialization.
        """
        return DomainBaseClientConfig(
            base_url=self.base_url,
            timeout=self.timeout or 30,
            rate_limit=RateLimitConfig(
                requests_per_second=self.rate_limit or 5.0,
            ),
        )


# =============================================================================
# Export/Import Configuration Base Classes
# =============================================================================


class BaseCsvExportConfig(BaseModel):
    """Base class for CSV export configuration.

    Provides common CSV export fields.

    Attributes:
        enabled: Whether CSV export is enabled.
        path: Output path for CSV file.
        delimiter: CSV field delimiter.
        header: Whether to include header row.
        encoding: File encoding.
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False,
        description="Whether CSV export is enabled",
    )
    path: str | None = Field(
        default=None,
        description="Output path for CSV file",
    )
    delimiter: str = Field(
        default=",",
        description="CSV field delimiter",
    )
    header: bool = Field(
        default=True,
        description="Whether to include header row",
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding",
    )


class BaseFilterColumnSchema(BaseModel):
    """Base class for filter column configuration.

    Represents a single column mapping for input filtering.

    Attributes:
        column_name: Column name in CSV containing filter IDs.
        filter_field: API field name to filter by.
    """

    model_config = ConfigDict(extra="ignore")

    column_name: str = Field(description="Column name in CSV containing filter IDs")
    filter_field: str = Field(description="API field name to filter by")


class BaseInputFilterConfig(BaseModel):
    """Base class for input filter configuration.

    Provides common input filter fields for both inline pipeline configs
    and standalone filter config files.

    Supports both single-column and multi-column filtering modes:
    - Single-column: Use column_name and filter_field directly
    - Multi-column: Use columns list for AND-logic filtering

    Attributes:
        enabled: Whether input filtering is enabled.
        source_path: Path to CSV file with filter IDs.
        column_name: CSV column with primary IDs (single-column mode).
        filter_field: API field to filter by (single-column mode).
        columns: List of columns for multi-column mode.
        batch_size: Number of IDs per API request.
        fallback_column: Fallback search field (e.g., title).
    """

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False,
        description="Whether input filtering is enabled",
    )
    source_path: str | None = Field(
        default=None,
        description="Path to CSV file with filter IDs",
    )
    # Single-column mode (backward compatibility)
    column_name: str | None = Field(
        default=None,
        description="Column name in CSV containing filter IDs (single-column mode)",
    )
    filter_field: str | None = Field(
        default=None,
        description="API field name to filter by (single-column mode)",
    )
    # Multi-column mode
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
    # Fallback support (e.g., DOI → title search)
    fallback_column: str | None = Field(
        default=None,
        description="Column name for fallback search when primary lookup fails",
    )

    @model_validator(mode="after")
    def validate_column_config(self) -> BaseInputFilterConfig:
        """Validate that either columns or column_name/filter_field is provided."""
        if not self.enabled:
            return self
        if self.columns:
            # Multi-column mode - columns provided
            return self
        if self.column_name and self.filter_field:
            # Single-column mode - backward compatibility
            return self
        # Neither mode configured - raise error
        raise ValueError(
            "Either 'columns' list or both 'column_name' and 'filter_field' "
            "must be provided when filter is enabled"
        )

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert to domain InputFilterConfig dataclass.

        Returns:
            DomainInputFilterConfig: Immutable domain configuration.
        """
        from bioetl.domain.filtering.input_config import (
            FilterColumn as DomainFilterColumn,
        )
        from bioetl.domain.filtering.input_config import (
            InputFilterConfig as DomainInputFilterConfigImpl,
        )

        # Convert columns list to domain FilterColumn tuple
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


# =============================================================================
# Maintenance Configuration Base Classes
# =============================================================================


class BaseMaintenanceConfig(BaseModel):
    """Base class for maintenance configuration.

    Controls automatic VACUUM and other maintenance tasks after pipeline runs.

    Attributes:
        auto_vacuum: Enable automatic VACUUM after successful run.
        vacuum_retention_days: Minimum age of files to remove (days).
    """

    model_config = ConfigDict(extra="ignore")

    auto_vacuum: bool = Field(
        default=False,
        description="Enable automatic VACUUM after successful pipeline run",
    )
    vacuum_retention_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Minimum age of files to remove during VACUUM (days)",
    )


# =============================================================================
# Gold Filter Configuration Base Classes
# =============================================================================


class BaseGoldRangeFilterConfig(BaseModel):
    """Base class for Gold range filter configuration.

    Attributes:
        min: Minimum value (inclusive by default).
        max: Maximum value (inclusive by default).
        include_min: Whether to include minimum value.
        include_max: Whether to include maximum value.
    """

    model_config = ConfigDict(extra="ignore")

    min: float | None = Field(
        default=None,
        description="Minimum value",
    )
    max: float | None = Field(
        default=None,
        description="Maximum value",
    )
    include_min: bool = Field(
        default=True,
        description="Whether to include minimum value",
    )
    include_max: bool = Field(
        default=True,
        description="Whether to include maximum value",
    )


class BaseGoldListLengthFilterConfig(BaseModel):
    """Base class for Gold list length filter configuration.

    Attributes:
        min: Minimum list length.
        max: Maximum list length.
    """

    model_config = ConfigDict(extra="ignore")

    min: int | None = Field(
        default=None,
        description="Minimum list length",
    )
    max: int | None = Field(
        default=None,
        description="Maximum list length",
    )


class BaseGoldListContainsFilterConfig(BaseModel):
    """Base class for Gold list contains filter configuration.

    Attributes:
        values: Values that must be present in the list.
        mode: Match mode ('all' or 'any').
    """

    model_config = ConfigDict(extra="ignore")

    values: list[str] = Field(
        description="Values that must be present in the list",
    )
    mode: Literal["all", "any"] = Field(
        default="all",
        description="Match mode ('all' or 'any')",
    )


class BaseGoldColumnFilterConfig(BaseModel):
    """Base class for Gold column filter configuration.

    Supports extended operators for column filtering:
    - in: value must be in the allowed list (default)
    - not_in: value must not be in the excluded list
    - is_null: value must be None or empty string
    - is_not_null: value must not be None or empty string
    - is_empty: value must be "empty" (None, "", [], {})
    - is_not_empty: value must not be "empty"

    Attributes:
        operator: Filter operator.
        values: Allowed/excluded values (for in/not_in operators).
    """

    model_config = ConfigDict(extra="ignore")

    operator: Literal[
        "in", "not_in", "is_null", "is_not_null", "is_empty", "is_not_empty"
    ] = Field(
        default="in",
        description="Filter operator",
    )
    values: list[str] | None = Field(
        default=None,
        description="Allowed/excluded values (for in/not_in operators)",
    )

    @model_validator(mode="after")
    def validate_operator_values(self) -> BaseGoldColumnFilterConfig:
        """Validate that values are provided for IN/NOT_IN operators."""
        if self.operator in ("in", "not_in") and not self.values:
            raise ValueError(f"values required for operator '{self.operator}'")
        if (
            self.operator in ("is_null", "is_not_null", "is_empty", "is_not_empty")
            and self.values is not None
        ):
            raise ValueError(f"values must be None for operator '{self.operator}'")
        return self


class BaseGoldFiltersConfig(BaseModel):
    """Base class for Gold filters configuration.

    Provides common Gold filter fields for both inline pipeline configs
    and standalone filter config files.

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

    model_config = ConfigDict(extra="ignore")

    columns: dict[str, list[str] | BaseGoldColumnFilterConfig] = Field(
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
        """Convert to domain GoldFilterConfig dataclass.

        Returns:
            GoldFilterConfig: Immutable domain configuration.
        """
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
                # Legacy format: list of values -> IN operator
                column_filters.append(
                    GoldColumnFilter(
                        column=col,
                        operator=FilterOperator.IN,
                        values=frozenset(cfg),
                    )
                )
            else:
                # New format: GoldColumnFilterConfig
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
    "BaseApiConfig",
    "BaseCircuitBreakerConfig",
    "BaseClientConfig",
    "BaseCsvExportConfig",
    "BaseDQConfig",
    "BaseDQThresholds",
    "BaseFilterColumnSchema",
    "BaseGoldColumnFilterConfig",
    "BaseGoldFiltersConfig",
    "BaseGoldListContainsFilterConfig",
    "BaseGoldListLengthFilterConfig",
    "BaseGoldRangeFilterConfig",
    "BaseInputFilterConfig",
    "BaseMaintenanceConfig",
    "BaseRateLimitConfig",
]
