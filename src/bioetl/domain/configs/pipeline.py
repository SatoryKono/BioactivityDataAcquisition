"""Pipeline configuration models (domain layer, no I/O)."""

from __future__ import annotations

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
    from bioetl.domain.configs.execution import ExecutionConfig
    from bioetl.domain.configs.manifest import PipelineManifest
    from bioetl.domain.pipelines.types import PipelineType
    from bioetl.domain.transform.contracts import NormalizationConfigProviderProtocol

# Import bounded context configs
from bioetl.domain.configs.data_flow import DataFlowConfig
from bioetl.domain.configs.identity import PipelineIdentityConfig
from bioetl.domain.configs.pipeline_options import NormalizationConfig, TransformConfig
from bioetl.domain.configs.sink import DataSinkConfig, OutputOptionsConfig
from bioetl.domain.configs.source import CsvInputConfig, DataSourceConfig


class PaginationConfig(BaseModel):
    """Pagination configuration."""

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


class ProviderHttpConfig(HttpClientConfig):
    """HTTP configuration for a specific provider with base URL."""

    base_url: str

    model_config = ConfigDict(frozen=True, extra="forbid")


class StorageConfig(BaseModel):
    """Storage path configuration."""

    output_path: str = "./data/output"
    cache_path: str = "./data/cache"
    temp_path: str = "./data/temp"

    model_config = ConfigDict(extra="forbid")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    structured: bool = True
    redact_secrets: bool = True

    model_config = ConfigDict(extra="forbid")


class MetricsConfig(BaseModel):
    """Metrics export configuration."""

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
    """Determinism configuration."""

    stable_sort: bool = True
    utc_timestamps: bool = True
    canonical_json: bool = True
    atomic_writes: bool = True

    model_config = ConfigDict(extra="forbid")


class QualityControlConfig(BaseModel):
    """Quality control configuration.

    This is the canonical name for QC configuration in the domain model.
    """

    enable_quality_report: bool = True
    enable_correlation_report: bool = True
    min_coverage: float = 0.85

    model_config = ConfigDict(extra="forbid")


class CanonicalizationConfig(BaseModel):
    """Canonicalization configuration for hashing."""

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
    """Business key configuration."""

    serialization: Literal["json_array", "json_object"] = "json_array"
    use_concatenation: bool = False

    model_config = ConfigDict(extra="forbid")


class HashingConfig(BaseModel):
    """Hashing configuration."""

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
    """Interface feature flags."""

    rest_interface_enabled: bool = False
    mq_interface_enabled: bool = False

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
    """Base strict provider configuration.

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
    def client(self) -> ProviderHttpConfig:
        """Backward compatibility: access http config via client property."""
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
    """ChEMBL source configuration."""

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
        """Compute effective batch size with constraints."""

        effective_batch = self.batch_size or hard_cap or 25

        if hard_cap is not None:
            effective_batch = min(effective_batch, hard_cap)

        if limit is not None:
            effective_batch = min(effective_batch, limit)

        return effective_batch


class DummyProviderConfig(BaseProviderConfig):
    """Dummy provider configuration for tests and templates."""

    provider: Literal["dummy"] = "dummy"


ProviderConfigUnion = Annotated[
    ChemblSourceConfig | DummyProviderConfig,
    Field(discriminator="provider"),
]


class RuntimeConfig(BaseModel):
    """Runtime and data source section."""

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


class ObservabilityConfig(BaseModel):
    """Logging and metrics section."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    model_config = ConfigDict(extra="forbid")


class QualityConfig(BaseModel):
    """Quality and determinism section."""

    determinism: DeterminismConfig = Field(default_factory=DeterminismConfig)
    quality_control: QualityControlConfig = Field(
        default_factory=QualityControlConfig, alias="qc"
    )
    hashing: HashingConfig = Field(default_factory=HashingConfig)
    normalization: NormalizationConfig = Field(default_factory=NormalizationConfig)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class FeatureFlagsConfig(BaseModel):
    """Interface features section."""

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
        """Allow flat feature flags without wrapper."""

        if not isinstance(data, dict):
            return data

        if "features" in data and isinstance(data["features"], dict):
            merged = {k: v for k, v in data.items() if k != "features"}
            data = {**data["features"], **merged}

        if "interfaces" not in data and "features" not in data:
            return {"interfaces": data}
        return data


class PipelineConfig(BaseModel):
    """Aggregate root for pipeline configuration.

    DEPRECATED: Use PipelineManifest for new code.

    This class is maintained for backward compatibility.
    New code should use PipelineManifest which has cleaner decomposition:
    - ExecutionConfig groups stages + runtime + transform
    - Observability and features are injected via DI, not in manifest

    Use to_manifest() to convert to new format, from_manifest() to create
    from PipelineManifest for backward compatibility.

    Composes specialized bounded context configurations.
    Contains no business logic, only structure.

    Breaking Changes (v2.0):
        - Access via decomposed sections:
          config.identity.entity, config.source.input_mode, etc.
        - Removed 20+ backward compatibility property accessors
        - Only convenience accessors for entity and provider remain

    Breaking Changes (v2.1):
        - source and sink are now grouped into data_flow section
        - Backward compatibility via .source and .sink properties

    Sections:
        identity: Pipeline identification (pipeline_id, provider, entity, primary_key)
        data_flow: Data flow settings (source + sink aggregate)
        stages: Pipeline stage flags (extract, transform, load)
        runtime: Execution settings (pagination, http, storage)
        observability: Logging and metrics
        quality: QC, hashing, normalization, determinism
        features: Feature flags
        transform: Transform stage settings
        provider_config: Provider-specific configuration

    Backward Compatibility:
        .source -> data_flow.source
        .sink -> data_flow.sink

    See Also:
        PipelineManifest: New recommended config aggregate.
    """

    # Core bounded context configs
    identity: PipelineIdentityConfig
    data_flow: DataFlowConfig
    stages: PipelineStagesConfig = Field(default_factory=PipelineStagesConfig)

    # Existing structured sections
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    transform: TransformConfig = Field(default_factory=TransformConfig)

    # Provider-specific config
    provider_config: ProviderConfigUnion | None = None

    # Schema configuration
    fields: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    # =========================================================================
    # Backward compatibility properties for data_flow decomposition
    # =========================================================================

    @property
    def source(self) -> DataSourceConfig:
        """Access source from data_flow section.

        Backward compatibility property for v2.0 code that accessed
        config.source directly.
        """
        return self.data_flow.source

    @property
    def sink(self) -> DataSinkConfig:
        """Access sink from data_flow section.

        Backward compatibility property for v2.0 code that accessed
        config.sink directly.
        """
        return self.data_flow.sink

    @sink.setter
    def sink(self, value: DataSinkConfig) -> None:
        """Allow updating sink while keeping DataFlowConfig frozen.

        Creates a new DataFlowConfig with the provided sink and assigns it,
        so callers can override output paths in tests/CLI without mutating
        the frozen DataFlowConfig instance.
        """
        self.data_flow = self.data_flow.model_copy(update={"sink": value})

    # =========================================================================
    # Convenience accessors (minimal, no backward compatibility)
    # =========================================================================

    @property
    def entity(self) -> str:
        """Access entity from identity section."""
        return str(self.identity.entity)

    @property
    def provider(self) -> str:
        """Access provider from identity section."""
        prov = self.identity.provider
        return prov.value if hasattr(prov, "value") else str(prov)

    @property
    def id(self) -> str:
        """Access pipeline_id from identity section."""
        return str(self.identity.pipeline_id)

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
    def serialization_mode(self) -> str:
        """Shortcut for transform.serialization_mode."""
        return self.transform.serialization_mode

    # =========================================================================
    # Execution aggregate (groups stages + runtime + transform)
    # =========================================================================

    @property
    def execution(self) -> "ExecutionConfig":
        """Aggregate accessor for all execution-related settings.

        Combines stages, runtime, and transform into a single cohesive
        ExecutionConfig object. This provides a unified interface for
        code that needs to work with execution settings as a group.

        Returns:
            ExecutionConfig: Immutable aggregate of execution settings

        Example:
            ```python
            if config.execution.is_extract_enabled:
                batch_size = config.execution.effective_batch_size
            ```
        """
        from bioetl.domain.configs.execution import ExecutionConfig

        return ExecutionConfig(
            stages=self.stages,
            runtime=self.runtime,
            transform=self.transform,
        )

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
        if self.provider_config is None:
            raise ValueError("provider_config is not set")
        return self.provider_config

    # =========================================================================
    # Validators
    # =========================================================================

    @model_validator(mode="after")
    def validate_provider_alignment(self) -> PipelineConfig:
        """Ensure provider_config provider aligns with identity.provider."""
        if self.provider_config is not None:
            if self.provider_config.provider != self.identity.provider:
                raise ValueError(
                    "provider_config.provider must match identity.provider"
                )
        return self

    # =========================================================================
    # Manifest conversion methods
    # =========================================================================

    def to_manifest(self) -> PipelineManifest:
        """Convert to new PipelineManifest format.

        Creates a PipelineManifest from this PipelineConfig, grouping
        execution-related settings into ExecutionConfig.

        Note: observability and features are NOT transferred to the manifest,
        as these should be injected via DI at runtime.

        Returns:
            PipelineManifest: New manifest with decomposed configuration.

        Example:
            >>> config = PipelineConfig(...)
            >>> manifest = config.to_manifest()
            >>> # Use manifest with new code
        """
        from bioetl.domain.configs.execution import ExecutionConfig
        from bioetl.domain.configs.manifest import PipelineManifest

        return PipelineManifest(
            identity=self.identity,
            data_flow=self.data_flow,
            execution=ExecutionConfig(
                stages=self.stages,
                runtime=self.runtime,
                transform=self.transform,
            ),
            quality=self.quality,
            provider_config=self.provider_config,
            fields=self.fields,
        )

    @classmethod
    def from_manifest(
        cls,
        manifest: PipelineManifest,
        *,
        observability: ObservabilityConfig | None = None,
        features: FeatureFlagsConfig | None = None,
    ) -> PipelineConfig:
        """Create from PipelineManifest for backward compatibility.

        This factory method enables using PipelineManifest with code
        that still expects PipelineConfig.

        Args:
            manifest: PipelineManifest instance.
            observability: Optional observability config.
                Defaults to ObservabilityConfig().
            features: Optional feature flags config.
                Defaults to FeatureFlagsConfig().

        Returns:
            PipelineConfig: Legacy configuration object.

        Example:
            >>> manifest = PipelineManifest(...)
            >>> config = PipelineConfig.from_manifest(manifest)
            >>> # Use config with legacy code
        """
        return cls(
            identity=manifest.identity,
            data_flow=manifest.data_flow,
            stages=manifest.execution.stages,
            runtime=manifest.execution.runtime,
            transform=manifest.execution.transform,
            quality=manifest.quality,
            provider_config=manifest.provider_config,
            fields=manifest.fields,
            observability=observability or ObservabilityConfig(),
            features=features or FeatureFlagsConfig(),
        )


__all__ = [
    # Main config
    "PipelineConfig",
    # Bounded context configs (re-exported for convenience)
    "PipelineIdentityConfig",
    "DataFlowConfig",
    "DataSourceConfig",
    "DataSinkConfig",
    "OutputOptionsConfig",
    "CsvInputConfig",
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
    "PipelineStagesConfig",
    # Sub-section configs
    "PaginationConfig",
    "HttpClientConfig",
    "StorageConfig",
    "LoggingConfig",
    "MetricsConfig",
    "DeterminismConfig",
    "QualityControlConfig",
    "HashingConfig",
    "CanonicalizationConfig",
    "BusinessKeyConfig",
    "InterfaceFeaturesConfig",
    "NormalizationConfig",
    "TransformConfig",
]
