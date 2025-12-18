"""Schema validation for pipeline configuration.

Implements strict validation for pipeline YAML configurations using Pydantic.
Enforces Medallion Architecture constraints and operational limits.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class DQConfig(BaseModel):
    """Data Quality configuration."""

    soft_fail_threshold: float = Field(default=0.05, ge=0.0, le=1.0)
    hard_fail_threshold: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "DQConfig":
        if self.soft_fail_threshold >= self.hard_fail_threshold:
            raise ValueError(
                "soft_fail_threshold must be strictly less than hard_fail_threshold"
            )
        return self


class CircuitBreakerConfig(BaseModel):
    """Circuit Breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: int = Field(default=300, ge=60)


class CsvExportConfig(BaseModel):
    """Configuration for CSV export."""

    enabled: bool = True
    path: str | None = None
    delimiter: str = ","
    header: bool = True
    encoding: str = "utf-8"


class SinkLayerConfig(BaseModel):
    """Configuration for a specific data layer (Bronze, Silver, Gold)."""

    enabled: bool = True
    path: str | None = None
    format: Literal["jsonl", "delta", "parquet"] = "delta"
    mode: str | None = None  # Validated by specific layer validators
    save_json: bool = False
    csv_export: CsvExportConfig | None = None


class PipelineYamlConfig(BaseModel):
    """Strict schema for pipeline YAML configuration.

    Enforces rules from RULES.md.
    """

    pipeline_name: str
    provider: str
    entity_type: str
    version: str = "v1"

    # Execution parameters
    batch_size: int = Field(default=100, ge=1, le=5000)
    checkpoint_interval: int = Field(default=1000, ge=100)

    # DQ & Reliability
    dq: DQConfig = Field(default_factory=DQConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

    # Storage
    primary_keys: list[str]
    silver_table: str
    gold_table: str | None = None

    # Medallion Layers
    sink: dict[str, SinkLayerConfig] = Field(default_factory=dict)

    # Source Config (Preserved from merge)
    source: dict[str, Any] = Field(default_factory=dict)

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
