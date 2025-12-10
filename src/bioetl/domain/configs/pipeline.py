"""Pipeline configuration models (domain layer, no I/O)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from bioetl.domain.pipelines.types import PipelineType
    from bioetl.domain.transform.contracts import NormalizationConfigProviderProtocol

# Import NormalizationConfig from the dedicated normalization module
from bioetl.domain.configs.normalization import NormalizationConfig
from bioetl.domain.configs.transform import TransformConfig


class PaginationConfig(BaseModel):
    """Конфигурация пагинации."""

    limit: int = 1000
    offset: int = 0
    max_pages: int | None = None

    model_config = ConfigDict(extra="forbid")


class HttpClientConfig(BaseModel):
    """Unified HTTP client configuration (single source of truth).

    This class consolidates HttpClientSettings, HttpClientDefaults, and ClientConfig
    into a single configuration model.

    Field mapping from legacy classes:
        HttpClientSettings.timeout -> timeout_sec
        HttpClientSettings.retries -> max_retries
        HttpClientSettings.backoff -> backoff_factor
        HttpClientSettings.rate_limit -> rate_limit_per_sec
        HttpClientSettings.retry_enabled -> (deprecated, use max_retries > 0)
        ClientConfig.circuit_breaker_recovery_time -> circuit_breaker_recovery_sec
    """

    timeout_sec: PositiveFloat = 30.0
    max_retries: NonNegativeInt = 3
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)
    backoff_factor: float = 2.0
    backoff_max: float = 60.0
    rate_limit_per_sec: PositiveFloat = 2.5

    # Circuit breaker settings
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_sec: float = 30.0

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: Any) -> Any:
        """Support legacy field names for backward compatibility."""
        if not isinstance(data, dict):
            return data

        migrated = dict(data)

        # HttpClientSettings/HttpClientDefaults field mappings
        legacy_mappings = {
            "timeout": "timeout_sec",
            "retries": "max_retries",
            "backoff": "backoff_factor",
            "rate_limit": "rate_limit_per_sec",
            "circuit_breaker_recovery_time": "circuit_breaker_recovery_sec",
        }

        for old_name, new_name in legacy_mappings.items():
            if old_name in migrated and new_name not in migrated:
                value = migrated.pop(old_name)
                if old_name in ("timeout", "retries"):
                    value = float(value) if old_name == "timeout" else int(value)
                migrated[new_name] = value

        # Handle retry_enabled -> if False, set max_retries to 0
        if "retry_enabled" in migrated:
            retry_enabled = migrated.pop("retry_enabled")
            if not retry_enabled and "max_retries" not in migrated:
                migrated["max_retries"] = 0

        return migrated

    @property
    def retry_enabled(self) -> bool:
        """Backward compatibility property for retry_enabled."""
        return self.max_retries > 0


class ProviderHttpConfig(HttpClientConfig):
    """HTTP configuration for a specific provider with base URL."""

    base_url: str

    model_config = ConfigDict(frozen=True, extra="forbid")


# =============================================================================
# DEPRECATED: Legacy aliases for backward compatibility
# These will be removed in a future version
# =============================================================================

# Legacy alias - use HttpClientConfig instead
HttpClientSettings = ProviderHttpConfig

# Legacy alias - use HttpClientConfig instead
ClientConfig = HttpClientConfig


class HttpClientDefaults(HttpClientConfig):
    """DEPRECATED: Use HttpClientConfig directly.

    Shared HTTP client defaults - now just an alias for HttpClientConfig.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


HTTP_CLIENT_DEFAULTS = HttpClientConfig()


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


class InterfaceFeaturesConfig(BaseModel):
    """Фиче-флаги интерфейсов."""

    rest_interface_enabled: bool = False
    mq_interface_enabled: bool = False

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


# =============================================================================
# Decomposed Configuration Classes
# =============================================================================


class PipelineIdentity(BaseModel):
    """Pipeline identification and metadata.

    Groups fields that identify the pipeline and its data domain.
    """

    id: str
    provider: str
    entity: str
    primary_key: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("provider")
    @classmethod
    def validate_provider_known(cls, value: str) -> str:
        """Ensure provider identifier is known to the registry."""
        from bioetl.domain.providers import ProviderId

        known = {provider.value for provider in ProviderId}
        if value not in known:
            raise ValueError(f"Unknown provider: {value}")
        return value


class DataSourceConfig(BaseModel):
    """Data source configuration.

    Groups fields related to input data: mode, path, batching, CSV options.
    """

    input_mode: Literal["csv", "id_only", "auto_detect"]
    input_path: str | None = None
    batch_size: PositiveInt
    csv: CsvInputConfig = Field(default_factory=CsvInputConfig, alias="csv_options")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, value: str | None) -> str | None:
        """Normalize empty input path to None and ensure path string."""
        if value is None or value == "":
            return None
        path = Path(value)
        return str(path)

    @model_validator(mode="after")
    def validate_input_mode_requires_path(self) -> DataSourceConfig:
        """Validate that input_mode is compatible with provided paths."""
        if self.input_mode in {"csv", "id_only"} and not self.input_path:
            raise ValueError(
                "input_path must be provided when input_mode is 'csv' or 'id_only'"
            )
        return self

    @model_validator(mode="after")
    def validate_csv_header_required(self) -> DataSourceConfig:
        """Validate CSV header requirement for csv and auto_detect modes."""
        if self.input_mode == "csv" and not self.csv.header:
            raise ValueError("csv.header must be true when input_mode is 'csv'")

        if (
            self.input_mode == "auto_detect"
            and self.input_path
            and not self.csv.header
        ):
            raise ValueError(
                "csv.header must be true when input_mode is 'auto_detect' "
                "and input_path is set"
            )
        return self


class OutputOptionsConfig(BaseModel):
    """Опции финальной записи артефактов."""

    converter: str | None = None

    model_config = ConfigDict(extra="forbid")


class DataSinkConfig(BaseModel):
    """Data sink configuration.

    Groups fields related to output: path, dry run mode, output options.
    """

    output_path: str
    dry_run: bool = False
    output: OutputOptionsConfig = Field(default_factory=OutputOptionsConfig)

    model_config = ConfigDict(extra="forbid")


class PipelineStagesConfig(BaseModel):
    """Pipeline stages configuration.

    Explicit flags for enabling/disabling ETL stages.
    """

    extract: bool | None = None
    transform: bool | None = None
    load: bool | None = None

    model_config = ConfigDict(extra="forbid")


class BaseProviderConfig(BaseModel):
    """Базовая строгая конфигурация провайдера.

    Uses HttpClientConfig as the single source of truth for HTTP settings.
    Legacy fields (http_client, client) are provided for backward compatibility.
    """

    provider: Literal["chembl", "dummy"]
    http: ProviderHttpConfig

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_config(cls, data: Any) -> Any:
        """Support legacy formats: http_client, client, or flat fields."""
        if not isinstance(data, dict):
            return data

        migrated = dict(data)

        # Collect HTTP config values from various sources
        http_config: dict[str, Any] = {}

        # If http is already set, extract its values as base
        if "http" in migrated:
            existing_http = migrated.pop("http")
            if isinstance(existing_http, dict):
                http_config.update(existing_http)
            elif hasattr(existing_http, "model_dump"):
                http_config.update(existing_http.model_dump())

        # Priority 1: http_client (legacy HttpClientSettings)
        if "http_client" in migrated:
            legacy_http = migrated.pop("http_client")
            if isinstance(legacy_http, dict):
                for k, v in legacy_http.items():
                    if k not in http_config:
                        http_config[k] = v
            elif hasattr(legacy_http, "model_dump"):
                for k, v in legacy_http.model_dump().items():
                    if k not in http_config:
                        http_config[k] = v

        # Priority 2: client (legacy ClientConfig)
        if "client" in migrated:
            legacy_client = migrated.pop("client")
            if isinstance(legacy_client, dict):
                for k, v in legacy_client.items():
                    if k not in http_config:
                        http_config[k] = v
            elif hasattr(legacy_client, "model_dump"):
                for k, v in legacy_client.model_dump().items():
                    if k not in http_config:
                        http_config[k] = v

        # Priority 3: Flat fields at root level
        flat_fields = (
            "base_url",
            "timeout_sec",
            "timeout",
            "max_retries",
            "retries",
            "rate_limit_per_sec",
            "rate_limit",
            "backoff_factor",
            "backoff",
            "retry_enabled",
            "retry_on_status",
            "backoff_max",
            "circuit_breaker_enabled",
            "circuit_breaker_threshold",
            "circuit_breaker_recovery_sec",
            "circuit_breaker_recovery_time",
        )
        for field in flat_fields:
            if field in migrated:
                if field not in http_config:
                    http_config[field] = migrated.pop(field)
                else:
                    # Remove duplicate field if already in http_config
                    migrated.pop(field)

        if http_config:
            migrated["http"] = http_config

        return migrated

    @property
    def base_url(self) -> str:
        """Backward compatibility: access base_url from http config."""
        return self.http.base_url

    @property
    def http_client(self) -> ProviderHttpConfig:
        """DEPRECATED: Use .http instead. Legacy alias for http config."""
        return self.http

    @property
    def client(self) -> HttpClientConfig:
        """DEPRECATED: Use .http instead. Legacy alias for http config."""
        return self.http

    @field_validator("provider")
    @classmethod
    def validate_provider_known(cls, value: str) -> str:
        """Ensure provider identifier is known to the registry."""
        from bioetl.domain.providers import ProviderId

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
    fallbacks: dict[str, list[str]] | None = None

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
    http: HttpClientConfig = Field(default_factory=HttpClientConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    csv: CsvInputConfig = Field(default_factory=CsvInputConfig, alias="csv_options")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def migrate_client_to_http(cls, data: Any) -> Any:
        """Support legacy 'client' field name."""
        if not isinstance(data, dict):
            return data
        if "client" in data and "http" not in data:
            data = dict(data)
            data["http"] = data.pop("client")
        return data

    @property
    def client(self) -> HttpClientConfig:
        """DEPRECATED: Use .http instead. Legacy alias for backward compatibility."""
        return self.http


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

    @property
    def rest_interface_enabled(self) -> bool:
        """Backwards-compatible access to REST flag."""

        return self.interfaces.rest_interface_enabled

    @rest_interface_enabled.setter
    def rest_interface_enabled(self, value: bool) -> None:
        self.interfaces.rest_interface_enabled = value

    @property
    def mq_interface_enabled(self) -> bool:
        """Backwards-compatible access to MQ flag."""

        return self.interfaces.mq_interface_enabled

    @mq_interface_enabled.setter
    def mq_interface_enabled(self, value: bool) -> None:
        self.interfaces.mq_interface_enabled = value

    @model_validator(mode="before")
    @classmethod
    def migrate_inline_flags(cls, data: Any) -> Any:
        """Позволяет передавать плоские фиче-флаги без обёртки."""

        if not isinstance(data, dict):
            return data

        if "features" in data and isinstance(data["features"], dict):
            merged = {k: v for k, v in data.items() if k != "features"}
            data = {**data["features"], **merged}

        if "interfaces" not in data and "features" not in data:
            return {"interfaces": data}
        return data


class PipelineConfig(BaseModel):
    """Decomposed pipeline configuration for BioETL.

    Uses composition of bounded context configs:
    - identity: Pipeline identification (id, provider, entity, primary_key)
    - source: Data source settings (input_mode, input_path, batch_size, csv)
    - sink: Data sink settings (output_path, dry_run, output options)
    - stages: Pipeline stage flags (extract, transform, load)
    - runtime: Execution settings (pagination, http, storage)
    - observability: Logging and metrics
    - quality: QC, hashing, normalization, determinism
    - features: Feature flags
    - transform: Transform stage settings
    """

    # Decomposed sections
    identity: PipelineIdentity
    source: DataSourceConfig
    sink: DataSinkConfig
    stages: PipelineStagesConfig = Field(default_factory=PipelineStagesConfig)

    # Existing structured sections
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    transform: TransformConfig = Field(default_factory=TransformConfig)

    # Provider-specific config
    provider_config: ProviderConfigUnion

    # Schema configuration
    fields: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    # =========================================================================
    # Backward compatibility properties (delegating to decomposed sections)
    # =========================================================================

    @property
    def id(self) -> str:
        """Backward compatibility: access id from identity."""
        return self.identity.id

    @id.setter
    def id(self, value: str) -> None:
        """Backward compatibility: set id in identity."""
        object.__setattr__(self.identity, "id", value)

    @property
    def provider(self) -> str:
        """Backward compatibility: access provider from identity."""
        return self.identity.provider

    @provider.setter
    def provider(self, value: str) -> None:
        """Backward compatibility: set provider in identity."""
        object.__setattr__(self.identity, "provider", value)

    @property
    def entity(self) -> str:
        """Backward compatibility: access entity from identity."""
        return self.identity.entity

    @entity.setter
    def entity(self, value: str) -> None:
        """Backward compatibility: set entity in identity."""
        object.__setattr__(self.identity, "entity", value)

    @property
    def primary_key(self) -> str | None:
        """Backward compatibility: access primary_key from identity."""
        return self.identity.primary_key

    @primary_key.setter
    def primary_key(self, value: str | None) -> None:
        """Backward compatibility: set primary_key in identity."""
        object.__setattr__(self.identity, "primary_key", value)

    @property
    def input_mode(self) -> Literal["csv", "id_only", "auto_detect"]:
        """Backward compatibility: access input_mode from source."""
        return self.source.input_mode

    @input_mode.setter
    def input_mode(self, value: Literal["csv", "id_only", "auto_detect"]) -> None:
        """Backward compatibility: set input_mode in source."""
        object.__setattr__(self.source, "input_mode", value)

    @property
    def input_path(self) -> str | None:
        """Backward compatibility: access input_path from source."""
        return self.source.input_path

    @input_path.setter
    def input_path(self, value: str | None) -> None:
        """Backward compatibility: set input_path in source."""
        object.__setattr__(self.source, "input_path", value)

    @property
    def batch_size(self) -> int:
        """Backward compatibility: access batch_size from source."""
        return self.source.batch_size

    @batch_size.setter
    def batch_size(self, value: int) -> None:
        """Backward compatibility: set batch_size in source."""
        object.__setattr__(self.source, "batch_size", value)

    @property
    def output_path(self) -> str:
        """Backward compatibility: access output_path from sink."""
        return self.sink.output_path

    @output_path.setter
    def output_path(self, value: str) -> None:
        """Backward compatibility: set output_path in sink."""
        object.__setattr__(self.sink, "output_path", value)

    @property
    def dry_run(self) -> bool:
        """Backward compatibility: access dry_run from sink."""
        return self.sink.dry_run

    @dry_run.setter
    def dry_run(self, value: bool) -> None:
        """Backward compatibility: set dry_run in sink."""
        object.__setattr__(self.sink, "dry_run", value)

    @property
    def output(self) -> OutputOptionsConfig:
        """Backward compatibility: access output from sink."""
        return self.sink.output

    @output.setter
    def output(self, value: OutputOptionsConfig) -> None:
        """Backward compatibility: set output in sink."""
        object.__setattr__(self.sink, "output", value)

    @property
    def csv_options(self) -> CsvInputConfig:
        """Backward compatibility: access csv from source."""
        return self.source.csv

    @csv_options.setter
    def csv_options(self, value: CsvInputConfig) -> None:
        """Backward compatibility: set csv in source."""
        object.__setattr__(self.source, "csv", value)

    @property
    def pipeline(self) -> dict[str, Any]:
        """Backward compatibility: access stages as dict."""
        return {
            "extract": self.stages.extract,
            "transform": self.stages.transform,
            "load": self.stages.load,
        }

    # =========================================================================
    # Backward compatibility for runtime section
    # =========================================================================

    @property
    def pagination(self) -> PaginationConfig:
        """Backward compatibility: access pagination from runtime."""
        return self.runtime.pagination

    @pagination.setter
    def pagination(self, value: PaginationConfig) -> None:
        """Backward compatibility: set pagination in runtime."""
        object.__setattr__(self.runtime, "pagination", value)

    @property
    def client(self) -> HttpClientConfig:
        """DEPRECATED: Use runtime.http instead."""
        return self.runtime.http

    @client.setter
    def client(self, value: HttpClientConfig) -> None:
        """DEPRECATED: Use runtime.http instead."""
        object.__setattr__(self.runtime, "http", value)

    @property
    def storage(self) -> StorageConfig:
        """Backward compatibility: access storage from runtime."""
        return self.runtime.storage

    @storage.setter
    def storage(self, value: StorageConfig) -> None:
        """Backward compatibility: set storage in runtime."""
        object.__setattr__(self.runtime, "storage", value)

    # =========================================================================
    # Backward compatibility for observability section
    # =========================================================================

    @property
    def logging(self) -> LoggingConfig:
        """Backward compatibility: access logging from observability."""
        return self.observability.logging

    @logging.setter
    def logging(self, value: LoggingConfig) -> None:
        """Backward compatibility: set logging in observability."""
        object.__setattr__(self.observability, "logging", value)

    @property
    def metrics(self) -> MetricsConfig:
        """Backward compatibility: access metrics from observability."""
        return self.observability.metrics

    @metrics.setter
    def metrics(self, value: MetricsConfig) -> None:
        """Backward compatibility: set metrics in observability."""
        object.__setattr__(self.observability, "metrics", value)

    # =========================================================================
    # Backward compatibility for quality section
    # =========================================================================

    @property
    def determinism(self) -> DeterminismConfig:
        """Backward compatibility: access determinism from quality."""
        return self.quality.determinism

    @determinism.setter
    def determinism(self, value: DeterminismConfig) -> None:
        """Backward compatibility: set determinism in quality."""
        object.__setattr__(self.quality, "determinism", value)

    @property
    def qc(self) -> QcConfig:
        """Backward compatibility: access qc from quality."""
        return self.quality.qc

    @qc.setter
    def qc(self, value: QcConfig) -> None:
        """Backward compatibility: set qc in quality."""
        object.__setattr__(self.quality, "qc", value)

    @property
    def hashing(self) -> HashingConfig:
        """Backward compatibility: access hashing from quality."""
        return self.quality.hashing

    @hashing.setter
    def hashing(self, value: HashingConfig) -> None:
        """Backward compatibility: set hashing in quality."""
        object.__setattr__(self.quality, "hashing", value)

    @property
    def normalization(self) -> NormalizationConfig:
        """Backward compatibility: access normalization from quality."""
        return self.quality.normalization

    @normalization.setter
    def normalization(self, value: NormalizationConfig) -> None:
        """Backward compatibility: set normalization in quality."""
        object.__setattr__(self.quality, "normalization", value)

    # =========================================================================
    # Backward compatibility for features section
    # =========================================================================

    @property
    def interface_features(self) -> InterfaceFeaturesConfig:
        """Backward compatibility: access interfaces from features."""
        return self.features.interfaces

    @interface_features.setter
    def interface_features(self, value: InterfaceFeaturesConfig) -> None:
        """Backward compatibility: set interfaces in features."""
        object.__setattr__(self.features, "interfaces", value)

    # =========================================================================
    # Computed properties
    # =========================================================================

    @property
    def pipeline_type(self) -> PipelineType:
        """Auto-detect pipeline type based on stages and flags."""
        from bioetl.domain.pipelines.types import PipelineType

        def _as_bool(v: bool | None, default: bool) -> bool:
            return v if isinstance(v, bool) else default

        # Auto-detection defaults
        extract_active_auto = bool(
            self.source.input_mode or self.source.input_path or self.provider_config
        )
        transform_active_auto = True
        load_active_auto = not self.sink.dry_run and bool(self.sink.output_path)

        extract_active = _as_bool(self.stages.extract, extract_active_auto)
        transform_active = _as_bool(self.stages.transform, transform_active_auto)
        load_active = _as_bool(self.stages.load, load_active_auto)

        if extract_active and not transform_active and not load_active:
            return PipelineType.EXTRACT_ONLY
        if transform_active and not extract_active:
            return PipelineType.TRANSFORM_ONLY
        return PipelineType.FULL

    @property
    def entity_name(self) -> str:
        """Alias for entity (backward compatibility)."""
        return self.identity.entity

    @property
    def serialization_mode(self) -> str:
        """Shortcut for transform.serialization_mode."""
        return self.transform.serialization_mode

    # =========================================================================
    # Public methods
    # =========================================================================

    def get_fields(self) -> list[dict[str, Any]]:
        """Return fields configuration."""
        return self.fields

    def get_normalization(self) -> NormalizationConfig:
        """Return normalization configuration section."""
        return self.quality.normalization

    def get_normalization_config_provider(self) -> NormalizationConfigProviderProtocol:
        """Return self to satisfy NormalizationConfigProviderProtocol."""
        return self

    def get_source_config(self, provider: str) -> ProviderConfigUnion:
        """Return provider-specific config ensuring provider matches."""
        if provider != self.identity.provider:
            raise ValueError(
                f"Requested provider '{provider}' does not match config provider "
                f"'{self.identity.provider}'"
            )
        return self.provider_config

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineConfig:
        """Ensure provider_config provider aligns with identity.provider."""
        if self.provider_config.provider != self.identity.provider:
            raise ValueError(
                "provider_config.provider must match identity.provider"
            )
        return self

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_layout(cls, data: Any) -> Any:
        """Migrate flat legacy fields into decomposed sections."""
        if not isinstance(data, dict):
            return data

        migrated = dict(data)

        # -----------------------------------------------------------------
        # Pack identity section from flat fields
        # -----------------------------------------------------------------
        if "identity" not in migrated:
            identity_fields = {}
            for field in ("id", "provider", "entity", "primary_key"):
                if field in migrated:
                    identity_fields[field] = migrated.pop(field)
            if identity_fields:
                migrated["identity"] = identity_fields

        # -----------------------------------------------------------------
        # Pack source section from flat fields
        # -----------------------------------------------------------------
        if "source" not in migrated:
            source_fields = {}
            for field in ("input_mode", "input_path", "batch_size"):
                if field in migrated:
                    source_fields[field] = migrated.pop(field)
            # Handle csv_options -> csv
            if "csv_options" in migrated:
                source_fields["csv"] = migrated.pop("csv_options")
            elif "csv" in migrated and "runtime" not in migrated:
                # csv at root level goes to source
                source_fields["csv"] = migrated.pop("csv")
            if source_fields:
                migrated["source"] = source_fields

        # -----------------------------------------------------------------
        # Pack sink section from flat fields
        # -----------------------------------------------------------------
        if "sink" not in migrated:
            sink_fields = {}
            for field in ("output_path", "dry_run"):
                if field in migrated:
                    sink_fields[field] = migrated.pop(field)
            # Handle output section
            if "output" in migrated:
                output_val = migrated.pop("output")
                if isinstance(output_val, dict):
                    sink_fields["output"] = output_val
            if sink_fields:
                migrated["sink"] = sink_fields

        # -----------------------------------------------------------------
        # Pack stages section from pipeline dict + migrate primary_key
        # -----------------------------------------------------------------
        if "pipeline" in migrated:
            pipeline_dict = migrated.pop("pipeline")
            if isinstance(pipeline_dict, dict):
                # Extract primary_key from pipeline dict -> identity
                if "primary_key" in pipeline_dict:
                    pk_from_pipeline = pipeline_dict.pop("primary_key")
                    # Only use if identity.primary_key not already set
                    if "identity" in migrated:
                        if migrated["identity"].get("primary_key") is None:
                            migrated["identity"]["primary_key"] = pk_from_pipeline
                    else:
                        migrated["identity"] = {"primary_key": pk_from_pipeline}

                # Extract stages
                if "stages" not in migrated:
                    stages_fields = {}
                    for field in ("extract", "transform", "load"):
                        if field in pipeline_dict:
                            stages_fields[field] = pipeline_dict[field]
                    if stages_fields:
                        migrated["stages"] = stages_fields

        # -----------------------------------------------------------------
        # Legacy runtime section packing
        # -----------------------------------------------------------------
        def _pack(section_key: str, keys: list[str]) -> None:
            existing_section = (
                migrated.get(section_key)
                if isinstance(migrated.get(section_key), dict)
                else None
            )
            keys_to_collect = list(keys)
            if section_key in keys_to_collect and existing_section is not None:
                keys_to_collect.remove(section_key)

            collected = {
                key: migrated.pop(key) for key in keys_to_collect if key in migrated
            }
            if not collected and existing_section is None:
                return

            target_section: dict[str, Any] = dict(existing_section or {})
            nested_from_collected = collected.pop(section_key, None)
            if isinstance(nested_from_collected, dict):
                target_section |= nested_from_collected

            for key, value in collected.items():
                if (
                    key in target_section
                    and isinstance(target_section[key], dict)
                    and isinstance(value, dict)
                ):
                    target_section[key] = {**target_section[key], **value}
                else:
                    target_section[key] = value

            if target_section:
                migrated[section_key] = target_section

        _pack("runtime", ["pagination", "client", "http", "storage"])
        _pack("observability", ["logging", "metrics"])
        _pack("quality", ["determinism", "qc", "hashing", "normalization"])
        _pack("features", ["features", "interface_features", "interfaces"])

        return migrated


__all__ = [
    # Decomposed config classes
    "PipelineIdentity",
    "DataSourceConfig",
    "DataSinkConfig",
    "PipelineStagesConfig",
    # Main config
    "PipelineConfig",
    # Provider configs
    "BaseProviderConfig",
    "ChemblSourceConfig",
    "DummyProviderConfig",
    "ProviderConfigUnion",
    "ProviderHttpConfig",
    # Section configs
    "RuntimeConfig",
    "ObservabilityConfig",
    "QualityConfig",
    "FeatureFlagsConfig",
    # Sub-section configs
    "PaginationConfig",
    "HttpClientConfig",
    "StorageConfig",
    "CsvInputConfig",
    "LoggingConfig",
    "MetricsConfig",
    "DeterminismConfig",
    "QcConfig",
    "HashingConfig",
    "CanonicalizationConfig",
    "BusinessKeyConfig",
    "InterfaceFeaturesConfig",
    "OutputOptionsConfig",
    "NormalizationConfig",
    # DEPRECATED: Legacy aliases (will be removed in future versions)
    "ClientConfig",  # Use HttpClientConfig
    "HttpClientDefaults",  # Use HttpClientConfig
    "HttpClientSettings",  # Use ProviderHttpConfig
    "HTTP_CLIENT_DEFAULTS",  # Use HttpClientConfig()
]
