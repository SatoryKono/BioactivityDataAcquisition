"""Schema validation for pipeline configuration.

Implements strict validation for pipeline YAML configurations using Pydantic.
Enforces Medallion Architecture constraints and operational limits.

Consolidation Pattern:
Each Pydantic model has a `to_domain()` method that converts to the corresponding
domain dataclass. This eliminates duplicate conversion logic and provides a clean
boundary between infrastructure (YAML parsing) and domain (business logic).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.configs.base import BaseClientConfig, RateLimitConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig

if TYPE_CHECKING:
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.filtering.gold_config import GoldFilterConfig
    from bioetl.domain.filtering.input_config import (
        InputFilterConfig as DomainInputFilterConfig,
    )


class DQConfig(BaseModel):
    """Data Quality configuration.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.

    Attributes:
        soft_fail_threshold: Error rate threshold for warnings (0.0-1.0).
        hard_fail_threshold: Error rate threshold for failures (0.0-1.0).
        strict_validation: If True, apply stricter validation rules.
            Use with caution as it may reject more records.

    """

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)
    strict_validation: bool = Field(
        default=False,
        description="Apply stricter validation rules (feature flag)",
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> DQConfig:
        """Validate that thresholds are between 0 and 1."""
        DomainDQConfig.validate_thresholds(
            soft_fail_threshold=self.soft_fail_threshold,
            hard_fail_threshold=self.hard_fail_threshold,
        )
        return self

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


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
    """

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass.

        Returns:
            DomainCircuitBreakerConfig: Immutable domain configuration.
        """
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = False
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"


class InputFilterConfig(BaseModel):
    """Configuration for input ID filtering from CSV.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
    """

    enabled: bool = False
    source_path: str | None = Field(
        default=None,
        description="Path to CSV file with filter IDs",
    )
    column_name: str = Field(
        default="id",
        description="Column name in CSV containing filter IDs",
    )
    filter_field: str = Field(
        default="molecule_chembl_id",
        description="API field name to filter by",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of IDs per API request",
    )

    def to_domain(self) -> DomainInputFilterConfig:
        """Convert to domain InputFilterConfig dataclass.

        Returns:
            DomainInputFilterConfig: Immutable domain configuration.
        """
        from bioetl.domain.filtering.input_config import (
            InputFilterConfig as DomainInputFilterConfigImpl,
        )

        return DomainInputFilterConfigImpl(
            enabled=self.enabled,
            source_path=self.source_path,
            column_name=self.column_name if self.enabled else None,
            filter_field=self.filter_field if self.enabled else None,
            batch_size=self.batch_size,
        )


class MaintenanceConfig(BaseModel):
    """Configuration for automated maintenance operations.

    Controls automatic VACUUM and other maintenance tasks after pipeline runs.

    Attributes:
        auto_vacuum: Enable automatic VACUUM after successful run.
        vacuum_retention_days: Minimum age of files to remove (days).
    """

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


class ApiConfig(BaseModel):
    """Configuration for API connection details.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
    """

    base_url: str | None = None
    rate_limit: float | None = None
    timeout: int | None = None

    def to_domain(self) -> BaseClientConfig:
        """Convert to domain BaseClientConfig dataclass.

        Returns:
            BaseClientConfig: Immutable domain configuration.
        """
        return BaseClientConfig(
            base_url=self.base_url,
            timeout=self.timeout or 30,
            rate_limit=RateLimitConfig(
                requests_per_second=self.rate_limit or 5.0,
            ),
        )


class RateLimitSourceConfig(BaseModel):
    """Rate limit configuration from source YAML.

    Pydantic model for parsing rate_limit section from configs/sources/*.yaml.
    """

    requests_per_second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)


class ClientSourceConfig(BaseModel):
    """HTTP client configuration from source YAML."""

    timeout_sec: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)


class ProviderSourceConfig(BaseModel):
    """Provider-specific configuration from source YAML.

    Pydantic model for parsing provider_config section from configs/sources/*.yaml.
    """

    provider: str | None = None
    base_url: str | None = None
    client: ClientSourceConfig = Field(default_factory=ClientSourceConfig)
    max_url_length: int = Field(default=2000, ge=500, le=8000)
    batch_size: int = Field(default=100, ge=1, le=5000)
    page_size: int = Field(default=1000, ge=100, le=10000)
    api_version: str | None = None
    default_email: str | None = None


class SourceConfig(BaseModel):
    """Configuration for the data source.

    Parses both pipeline source settings and configs/sources/*.yaml structure.
    The `rate_limit`, `circuit_breaker`, and `provider_config` fields capture
    settings from source configuration files that were previously ignored.
    """

    # Common fields
    load_strategy: Literal["full", "incremental"] = "full"
    search_term: str | None = None
    email: str | None = None
    api_key: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)

    # Source file fields (from configs/sources/*.yaml)
    type: Literal["api", "file"] = "api"
    batch_size: int = Field(default=100, ge=1, le=5000)
    rate_limit: RateLimitSourceConfig = Field(default_factory=RateLimitSourceConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    provider_config: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)


class SortByConfig(BaseModel):
    """Configuration for deterministic sorting.

    Example YAML:
        sort_by:
          columns: [target_chembl_id, pref_name]
          ascending: true
    """

    columns: list[str] = Field(default_factory=list)
    ascending: bool = True


class SinkLayerConfig(BaseModel):
    """Configuration for a specific data layer (Bronze, Silver, Gold)."""

    enabled: bool = True
    path: str | None = None
    format: Literal["jsonl", "delta", "parquet"] = "delta"
    mode: str | None = None
    save_json: bool = False
    csv_export: CsvExportConfig = Field(default_factory=CsvExportConfig)
    # Deterministic write settings
    primary_key: list[str] = Field(default_factory=list)
    partition_by: list[str] = Field(default_factory=list)
    sort_by: SortByConfig = Field(default_factory=SortByConfig)
    deterministic: bool = Field(
        default=True, description="Enable deterministic write order"
    )
    # Schema drift handling
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = Field(
        default="error", description="How to handle schema drift"
    )


class GoldRangeFilterConfig(BaseModel):
    """Schema for range filters in YAML."""

    min: float | None = None
    max: float | None = None
    include_min: bool = True
    include_max: bool = True


class GoldListLengthFilterConfig(BaseModel):
    """Schema for list length filters in YAML."""

    min: int | None = None
    max: int | None = None


class GoldListContainsFilterConfig(BaseModel):
    """Schema for list contains filters in YAML."""

    values: list[str]
    mode: Literal["all", "any"] = "all"


class GoldFiltersConfig(BaseModel):
    """Schema for gold_filters in YAML.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.
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
        from bioetl.domain.filtering import (
            GoldColumnFilter,
            GoldFilterConfig,
            GoldListContainsFilter,
            GoldListLengthFilter,
            GoldRangeFilter,
        )

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


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration.

    Pydantic model for YAML parsing. Use `to_domain()` to convert to domain dataclass.

    Note:
        The `to_domain()` method delegates to `yaml_config_to_domain()` in
        `bioetl.infrastructure.config` to avoid code duplication.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pipeline_name: str
    provider: str
    entity_type: str
    version: str = "v1"

    batch_size: int = Field(default=100, ge=1, le=5000)
    checkpoint_interval: int = Field(default=1000, ge=100)

    dq_rules: DQConfig = Field(
        default_factory=DQConfig,
        validation_alias=AliasChoices("dq_rules", "dq"),
        serialization_alias="dq_rules",
    )
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

    primary_keys: list[str] = Field(min_length=1)
    silver_table: str = Field(min_length=1)
    gold_table: str | None = Field(default=None, min_length=1)
    gold_filters: GoldFiltersConfig = Field(default_factory=GoldFiltersConfig)

    sink: dict[str, SinkLayerConfig] = Field(default_factory=dict)
    source: SourceConfig = Field(default_factory=SourceConfig)
    input_filter: InputFilterConfig = Field(default_factory=InputFilterConfig)
    maintenance: MaintenanceConfig = Field(default_factory=MaintenanceConfig)

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size limit."""
        if v > 5000:
            raise ValueError("batch_size cannot exceed 5000 records")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name format."""
        if not v.islower():
            raise ValueError("provider must be lowercase")
        return v

    @model_validator(mode="after")
    def validate_medallion_formats(self) -> PipelineYamlConfig:
        """Validate Medallion Architecture format constraints.

        RULES.md §2.1: Silver and Gold MUST use Delta Lake format.
        Bronze MAY use JSONL (preferred) or Delta.

        Raises:
            ValueError: If Silver or Gold layer uses Parquet format.
        """
        silver_config = self.sink.get("silver")
        gold_config = self.sink.get("gold")

        if silver_config and silver_config.format == "parquet":
            raise ValueError(
                "Silver layer MUST use 'delta' format (RULES.md §2.1). "
                "Parquet is not allowed for Silver layer."
            )

        if gold_config and gold_config.format == "parquet":
            raise ValueError(
                "Gold layer MUST use 'delta' format (RULES.md §2.1). "
                "Parquet is not allowed for Gold layer."
            )

        return self

    def to_domain(self) -> PipelineConfig:
        """Convert to domain PipelineConfig dataclass.

        Delegates to `yaml_config_to_domain()` in `bioetl.infrastructure.config`
        to avoid code duplication. This method provides a consistent API
        across all Pydantic models.

        Returns:
            PipelineConfig: Immutable domain configuration.
        """
        from bioetl.infrastructure.config import yaml_config_to_domain

        return yaml_config_to_domain(self)
