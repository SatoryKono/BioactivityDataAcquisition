"""Pipeline configuration models (domain layer, no I/O)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)

from bioetl.domain.configs.base import (
    ClientConfig,
    CsvInputOptions,
    DeterminismConfig,
    HashingConfig,
    InterfaceFeaturesConfig,
    LoggingConfig,
    MetricsConfig,
    NormalizationConfig,
    PaginationConfig,
    ProviderConfigUnion,
    QcConfig,
    StorageConfig,
)
from bioetl.domain.transform.contracts import NormalizationConfigProvider


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
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    qc: QcConfig = Field(default_factory=QcConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)
    features: InterfaceFeaturesConfig = Field(default_factory=InterfaceFeaturesConfig)

    pipeline: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def entity_name(self) -> str:
        return self.entity

    def as_normalization_config_provider(self) -> NormalizationConfigProvider:
        """Return self to satisfy NormalizationConfigProvider protocol."""

        return self

    def get_source_config(self, provider: str) -> ProviderConfigUnion:
        if provider != self.provider:
            raise ValueError(
                (
                    f"Requested provider '{provider}' does not match config provider "
                    f"'{self.provider}'"
                )
            )
        return self.provider_config

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        path = Path(value)
        return str(path)

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineConfig:
        if self.provider_config.provider != self.provider:
            raise ValueError("provider_config.provider must match top-level provider")
        return self

    @model_validator(mode="after")
    def validate_input_mode(self) -> PipelineConfig:
        if self.input_mode in {"csv", "id_only"} and not self.input_path:
            raise ValueError(
                "input_path must be provided when input_mode is 'csv' or 'id_only'"
            )

        if self.input_mode == "csv" and not self.csv_options.header:
            raise ValueError("csv_options.header must be true when input_mode is 'csv'")

        if (
            self.input_mode == "auto_detect"
            and self.input_path
            and not self.csv_options.header
        ):
            raise ValueError(
                (
                    "csv_options.header must be true when input_mode is 'auto_detect' "
                    "and input_path is set"
                )
            )

        return self


__all__ = ["PipelineConfig"]
