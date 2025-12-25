"""Schema validation for pipeline configuration.

Implements strict validation for pipeline YAML configurations using Pydantic.
Enforces Medallion Architecture constraints and operational limits.
"""

from __future__ import annotations

from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from bioetl.domain.config import DQConfig as DomainDQConfig


class DQConfig(BaseModel):
    """Data Quality configuration.

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


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = False
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"


class InputFilterConfig(BaseModel):
    """Configuration for input ID filtering from CSV."""

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


class ApiConfig(BaseModel):
    """Configuration for API connection details."""

    base_url: str | None = None
    rate_limit: float | None = None
    timeout: int | None = None


class SourceConfig(BaseModel):
    """Configuration for the data source."""

    load_strategy: Literal["full", "incremental"] = "full"
    search_term: str | None = None
    email: str | None = None
    api_key: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)


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
    """Schema for gold_filters in YAML."""

    columns: dict[str, list[str]] = Field(default_factory=dict)
    ranges: dict[str, GoldRangeFilterConfig] = Field(default_factory=dict)
    list_lengths: dict[str, GoldListLengthFilterConfig] = Field(default_factory=dict)
    list_contains: dict[str, GoldListContainsFilterConfig] = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)
    exclude_if_present: list[str] = Field(default_factory=list)


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration."""

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
