"""Строгие схемы конфигурации пайплайна."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator

from bioetl.schemas.provider_config_schema import (
    BaseProviderConfig,
    ChemblSourceConfig,
    ProviderConfigUnion,
)


class PaginationConfig(BaseModel):
    """Конфигурация пагинации."""

    limit: int = 1000
    offset: int = 0
    max_pages: int | None = None

    model_config = ConfigDict(extra="forbid")


class ClientConfig(BaseModel):
    """Конфигурация HTTP-клиента."""

    timeout: float = 30.0
    max_retries: int = 3
    rate_limit: float = 10.0
    backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5

    model_config = ConfigDict(extra="forbid")


class StorageConfig(BaseModel):
    """Конфигурация путей хранения файлов."""

    output_path: str = "./data/output"
    cache_path: str = "./data/cache"
    temp_path: str = "./data/temp"

    model_config = ConfigDict(extra="forbid")


class LoggingConfig(BaseModel):
    """Конфигурация логирования."""

    level: str = "INFO"
    structured: bool = True
    redact_secrets: bool = True

    model_config = ConfigDict(extra="forbid")


class DeterminismConfig(BaseModel):
    """Конфигурация детерминизма."""

    stable_sort: bool = True
    utc_timestamps: bool = True
    canonical_json: bool = True
    atomic_writes: bool = True

    model_config = ConfigDict(extra="forbid")


class QcConfig(BaseModel):
    """Конфигурация контроля качества."""

    enable_quality_report: bool = True
    enable_correlation_report: bool = True
    min_coverage: float = 0.85

    model_config = ConfigDict(extra="forbid")


class HashingConfig(BaseModel):
    """Конфигурация хеширования."""

    business_key_fields: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class NormalizationConfig(BaseModel):
    """Конфигурация нормализации данных."""

    case_sensitive_fields: list[str] = Field(default_factory=list)
    id_fields: list[str] = Field(default_factory=list)
    custom_normalizers: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class CsvInputOptions(BaseModel):
    """Опции CSV-ввода."""

    delimiter: str = ","
    header: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, value: str) -> str:
        if not value:
            raise ValueError("CSV delimiter must be a non-empty string")
        return value


class PipelineConfig(BaseModel):
    """Строгая конфигурация пайплайна BioETL."""

    id: str
    provider: str
    entity: str
    primary_key: str | None = None
    input_mode: Literal["csv", "id_only", "auto_detect"]
    input_path: str | None
    output_path: str
    batch_size: PositiveInt
    dry_run: bool = False
    provider_config: ProviderConfigUnion

    csv_options: CsvInputOptions = Field(default_factory=CsvInputOptions)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    client: ClientConfig = Field(default_factory=ClientConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    qc: QcConfig = Field(default_factory=QcConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)

    pipeline: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def entity_name(self) -> str:
        return self.entity

    def get_source_config(self, provider: str) -> BaseProviderConfig:
        if provider != self.provider:
            raise ValueError(
                f"Requested provider '{provider}' does not match config provider '{self.provider}'"
            )
        return self.provider_config

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        path = Path(value)
        if not path.exists():
            raise ValueError(f"Input path does not exist: {value}")
        return str(path)

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineConfig:
        if self.provider_config.provider != self.provider:
            raise ValueError(
                "provider_config.provider must match top-level provider"
            )
        return self

    @model_validator(mode="after")
    def validate_input_mode(self) -> PipelineConfig:
        if self.input_mode in {"csv", "id_only"} and not self.input_path:
            raise ValueError(
                "input_path must be provided when input_mode is 'csv' or 'id_only'"
            )

        if self.input_mode == "csv" and not self.csv_options.header:
            raise ValueError(
                "csv_options.header must be true when input_mode is 'csv'"
            )

        if (
            self.input_mode == "auto_detect"
            and self.input_path
            and not self.csv_options.header
        ):
            raise ValueError(
                "csv_options.header must be true when input_mode is 'auto_detect' and input_path is set"
            )

        return self


__all__ = [
    "ClientConfig",
    "CsvInputOptions",
    "DeterminismConfig",
    "HashingConfig",
    "LoggingConfig",
    "NormalizationConfig",
    "PaginationConfig",
    "PipelineConfig",
    "QcConfig",
    "StorageConfig",
    "ChemblSourceConfig",
    "ProviderConfigUnion",
]
