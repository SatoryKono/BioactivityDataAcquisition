"""Schema validation for pipeline configuration.

Implements strict validation for pipeline YAML configurations using Pydantic.
Enforces Medallion Architecture constraints and operational limits.
"""

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
    """Data Quality configuration."""

    soft_fail_threshold: float = Field(default=0.05)
    hard_fail_threshold: float = Field(default=0.20)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "DQConfig":
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
    """Configuration for input ID filtering from CSV.

    Allows filtering API requests by IDs loaded from a CSV file.
    CLI options can override these defaults.
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
    watermark_field: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)


class SinkLayerConfig(BaseModel):
    """Configuration for a specific data layer (Bronze, Silver, Gold)."""

    enabled: bool = True
    path: str | None = None
    format: Literal["jsonl", "delta", "parquet"] = "delta"
    mode: str | None = None  # Validated by specific layer validators
    save_json: bool = False  # For Bronze layer: save uncompressed JSON copy
    csv_export: CsvExportConfig = Field(default_factory=CsvExportConfig)


class GoldFiltersConfig(BaseModel):
    """Schema для gold_filters в YAML.

    Позволяет конфигурировать фильтры Gold слоя:
    - columns: колонки с допустимыми значениями (оператор "in")
    - required_fields: обязательные поля (не null)
    - exclude_if_present: исключающие поля

    Пример YAML:
        gold_filters:
          columns:
            standard_type: [IC50, Ki]
            assay_type: [B, F]
          required_fields:
            - standard_value
            - target_chembl_id
          exclude_if_present:
            - data_validity_comment
    """

    columns: dict[str, list[str]] = Field(default_factory=dict)
    required_fields: list[str] = Field(default_factory=list)
    exclude_if_present: list[str] = Field(default_factory=list)


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration.

    Enforces rules from RULES.md.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pipeline_name: str
    provider: str
    entity_type: str
    version: str = "v1"

    # Execution parameters
    batch_size: int = Field(default=100, ge=1, le=5000)
    checkpoint_interval: int = Field(default=1000, ge=100)

    # DQ & Reliability
    dq_rules: DQConfig = Field(
        default_factory=DQConfig,
        validation_alias=AliasChoices("dq_rules", "dq"),
        serialization_alias="dq_rules",
    )
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

    # Storage
    primary_keys: list[str] = Field(min_length=1)
    silver_table: str = Field(min_length=1)
    gold_table: str | None = Field(default=None, min_length=1)
    gold_filters: GoldFiltersConfig = Field(default_factory=GoldFiltersConfig)

    # Medallion Layers
    sink: dict[str, SinkLayerConfig] = Field(default_factory=dict)

    # Source Config
    source: SourceConfig = Field(default_factory=SourceConfig)

    # Input Filter Config (for CSV-based ID filtering)
    input_filter: InputFilterConfig = Field(default_factory=InputFilterConfig)

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v > 5000:
            raise ValueError("batch_size cannot exceed 5000 records")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if not v.islower():
            raise ValueError("provider must be lowercase")
        return v
