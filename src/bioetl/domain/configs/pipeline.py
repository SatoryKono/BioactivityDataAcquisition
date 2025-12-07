"""Pipeline configuration models (domain layer, no I/O)."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from bioetl.domain.providers import ProviderId
from bioetl.domain.transform.contracts import NormalizationConfigProviderProtocol


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
    circuit_breaker_recovery_time: float = 60.0

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


class MetricsConfig(BaseModel):
    """Конфигурация экспорта метрик."""

    enabled: bool = True
    port: int = 9108
    address: str = "0.0.0.0"

    model_config = ConfigDict(extra="forbid")

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        """Ensure metrics port is within valid TCP range."""

        if value <= 0 or value > 65535:
            raise ValueError("metrics.port must be between 1 and 65535")
        return value


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


class CanonicalizationConfig(BaseModel):
    """Конфигурация канонизации для хеширования."""

    format: Literal["canonical_json"] = "canonical_json"
    utf8: bool = True
    ensure_ascii: bool = False
    sort_keys_recursive: bool = True
    arrays_preserve_order: bool = True
    float_format: str = "%.15g"
    unicode_normalization: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC"
    missing_field_representation: str | None = None

    model_config = ConfigDict(extra="forbid")


class BusinessKeyConfig(BaseModel):
    """Конфигурация бизнес-ключа."""

    serialization: Literal["json_array", "json_object"] = "json_array"
    use_concatenation: bool = False

    model_config = ConfigDict(extra="forbid")


class HashingConfig(BaseModel):
    """Конфигурация хеширования."""

    algorithm: str = "blake2b"
    digest_size_bytes: int = 32
    output_encoding: str = "hex_lower"
    salt: str | None = None
    hash_version: str = "v1_blake2b_256"

    canonicalization: CanonicalizationConfig = Field(
        default_factory=CanonicalizationConfig
    )
    business_key: BusinessKeyConfig = Field(default_factory=BusinessKeyConfig)

    business_key_fields: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class NormalizationConfig(BaseModel):
    """Конфигурация нормализации данных."""

    case_sensitive_fields: list[str] = Field(default_factory=list)
    id_fields: list[str] = Field(default_factory=list)
    custom_normalizers: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class InterfaceFeaturesConfig(BaseModel):
    """Фиче-флаги интерфейсов."""

    rest_interface_enabled: bool = False
    mq_interface_enabled: bool = False
    enable_provider_loader_port: bool = False

    model_config = ConfigDict(extra="forbid")


class CsvInputConfig(BaseModel):
    """Конфигурация CSV-ввода."""

    delimiter: str = ","
    header: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, value: str) -> str:
        """Validate that CSV delimiter is a non-empty string."""

        if not value:
            raise ValueError("CSV delimiter must be a non-empty string")
        return value


class BaseProviderConfig(BaseModel):
    """Базовая строгая конфигурация провайдера."""

    provider: Literal["chembl", "pubchem", "uniprot", "dummy"]
    base_url: AnyHttpUrl
    timeout_sec: PositiveFloat
    max_retries: NonNegativeInt
    rate_limit_per_sec: PositiveFloat | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("provider")
    @classmethod
    def validate_provider_known(cls, value: str) -> str:
        """Ensure provider identifier is known to the registry."""

        known = {provider.value for provider in ProviderId}
        if value not in known:
            raise ValueError(f"Unknown provider: {value}")
        return value


class ChemblSourceConfig(BaseProviderConfig):
    """Конфигурация источника ChEMBL."""

    provider: Literal["chembl"] = "chembl"
    api_version: str | None = None
    max_url_length: PositiveInt | None = None
    page_size: PositiveInt | None = None
    batch_size: PositiveInt | None = None

    model_config = ConfigDict(extra="forbid")

    def resolve_effective_batch_size(
        self, limit: int | None = None, hard_cap: int | None = 25
    ) -> int:
        """Вычисляет эффективный размер батча с учётом ограничений."""

        effective_batch = self.batch_size or hard_cap or 25

        if hard_cap is not None:
            effective_batch = min(effective_batch, hard_cap)

        if limit is not None:
            effective_batch = min(effective_batch, limit)

        return effective_batch


class DummyProviderConfig(BaseProviderConfig):
    """Конфигурация фиктивного провайдера для тестов и шаблонов."""

    provider: Literal["dummy"] = "dummy"


ProviderConfigUnion = Annotated[
    ChemblSourceConfig | DummyProviderConfig,
    Field(discriminator="provider"),
]


class RuntimeConfig(BaseModel):
    """Секция исполнения и источников данных."""

    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    client: ClientConfig = Field(default_factory=ClientConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    csv: CsvInputConfig = Field(default_factory=CsvInputConfig, alias="csv_options")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ObservabilityConfig(BaseModel):
    """Секция логирования и метрик."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    model_config = ConfigDict(extra="forbid")


class QualityConfig(BaseModel):
    """Секция качества и детерминизма."""

    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    qc: QcConfig = Field(default_factory=QcConfig)
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)

    model_config = ConfigDict(extra="forbid")


class FeatureFlagsConfig(BaseModel):
    """Секция фичей интерфейсов."""

    interfaces: InterfaceFeaturesConfig = Field(
        default_factory=InterfaceFeaturesConfig, alias="features"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def migrate_inline_flags(cls, data: Any) -> Any:
        """Позволяет передавать плоские фиче-флаги без обёртки."""

        if isinstance(data, dict) and "interfaces" not in data and "features" not in data:
            return {"interfaces": data}
        return data


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

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)

    pipeline: dict[str, Any] = Field(default_factory=dict)
    fields: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def entity_name(self) -> str:
        """Return canonical entity name."""

        return self.entity

    @property
    def pagination(self) -> PaginationConfig:
        """Backwards compatible access to pagination section."""

        return self.runtime.pagination

    @pagination.setter
    def pagination(self, value: PaginationConfig) -> None:
        self.runtime.pagination = value

    @property
    def client(self) -> ClientConfig:
        """Backwards compatible access to client section."""

        return self.runtime.client

    @client.setter
    def client(self, value: ClientConfig) -> None:
        self.runtime.client = value

    @property
    def storage(self) -> StorageConfig:
        """Backwards compatible access to storage section."""

        return self.runtime.storage

    @storage.setter
    def storage(self, value: StorageConfig) -> None:
        self.runtime.storage = value

    @property
    def csv_options(self) -> CsvInputConfig:
        """Backwards compatible access to csv section."""

        return self.runtime.csv

    @csv_options.setter
    def csv_options(self, value: CsvInputConfig) -> None:
        self.runtime.csv = value

    @property
    def logging(self) -> LoggingConfig:
        """Backwards compatible access to logging section."""

        return self.observability.logging

    @logging.setter
    def logging(self, value: LoggingConfig) -> None:
        self.observability.logging = value

    @property
    def metrics(self) -> MetricsConfig:
        """Backwards compatible access to metrics section."""

        return self.observability.metrics

    @metrics.setter
    def metrics(self, value: MetricsConfig) -> None:
        self.observability.metrics = value

    @property
    def determinism(self) -> DeterminismConfig:
        """Backwards compatible access to determinism section."""

        return self.quality.determinism

    @determinism.setter
    def determinism(self, value: DeterminismConfig) -> None:
        self.quality.determinism = value

    @property
    def qc(self) -> QcConfig:
        """Backwards compatible access to QC section."""

        return self.quality.qc

    @qc.setter
    def qc(self, value: QcConfig) -> None:
        self.quality.qc = value

    @property
    def hashing(self) -> HashingConfig:
        """Backwards compatible access to hashing section."""

        return self.quality.hashing

    @hashing.setter
    def hashing(self, value: HashingConfig) -> None:
        self.quality.hashing = value

    @property
    def normalization(self) -> NormalizationConfig:
        """Backwards compatible access to normalization section."""

        return self.quality.normalization

    @normalization.setter
    def normalization(self, value: NormalizationConfig) -> None:
        self.quality.normalization = value

    @property
    def interface_features(self) -> InterfaceFeaturesConfig:
        """Backwards compatible access to interface features."""

        return self.features.interfaces

    @interface_features.setter
    def interface_features(self, value: InterfaceFeaturesConfig) -> None:
        self.features.interfaces = value

    def get_normalization(self) -> NormalizationConfig:
        """Return normalization configuration section."""

        return self.quality.normalization

    def get_fields(self) -> list[dict[str, Any]]:
        """Return fields configuration."""

        return self.fields

    def get_normalization_config_provider(self) -> NormalizationConfigProviderProtocol:
        """Return self to satisfy NormalizationConfigProviderProtocol."""

        return self

    def get_source_config(self, provider: str) -> ProviderConfigUnion:
        """Return provider-specific config ensuring provider matches."""

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
        """Normalize empty input path to None and ensure path string."""

        if value is None or value == "":
            return None
        path = Path(value)
        return str(path)

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineConfig:
        """Ensure provider_config provider aligns with top-level provider."""
        if self.provider_config.provider != self.provider:
            raise ValueError("provider_config.provider must match top-level provider")
        return self

    @model_validator(mode="after")
    def validate_input_mode(self) -> PipelineConfig:
        """Validate that input_mode is compatible with provided paths and headers."""

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

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_layout(cls, data: Any) -> Any:
        """Собирает устаревшие плоские ключи в вложенные секции."""

        if not isinstance(data, dict):
            return data

        migrated = dict(data)

        def _pack(section_key: str, keys: list[str]) -> None:
            if section_key in migrated:
                return
            collected = {key: migrated.pop(key) for key in keys if key in migrated}
            if collected:
                migrated[section_key] = collected

        _pack(
            "runtime",
            ["pagination", "client", "storage", "csv", "csv_options"],
        )
        _pack("observability", ["logging", "metrics"])
        _pack("quality", ["determinism", "qc", "hashing", "normalization"])
        _pack("features", ["features", "interface_features", "interfaces"])

        return migrated


__all__ = [
    "BaseProviderConfig",
    "BusinessKeyConfig",
    "CanonicalizationConfig",
    "ChemblSourceConfig",
    "ClientConfig",
    "CsvInputConfig",
    "DeterminismConfig",
    "DummyProviderConfig",
    "FeatureFlagsConfig",
    "HashingConfig",
    "InterfaceFeaturesConfig",
    "LoggingConfig",
    "MetricsConfig",
    "NormalizationConfig",
    "ObservabilityConfig",
    "PaginationConfig",
    "PipelineConfig",
    "ProviderConfigUnion",
    "QualityConfig",
    "RuntimeConfig",
    "QcConfig",
    "StorageConfig",
]
