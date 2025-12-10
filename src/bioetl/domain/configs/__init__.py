"""Domain configuration models (pure, without I/O)."""

from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.configs.defaults import (
    ClientDefaultsConfig,
    DefaultsConfig,
    HashingDefaultsConfig,
    HttpDefaultsConfig,
    NetworkDefaultsConfig,
    NetworkHttpDefaultsConfig,
    NormalizationDefaultsConfig,
    SourceDefaultsConfig,
    SourcesDefaultsConfig,
)

# Bounded context configs
from bioetl.domain.configs.identity import PipelineIdentityConfig
from bioetl.domain.configs.normalization import NormalizationConfig
from bioetl.domain.configs.pipeline import (
    HTTP_CLIENT_DEFAULTS,
    BaseProviderConfig,
    BusinessKeyConfig,
    CanonicalizationConfig,
    ChemblSourceConfig,
    ClientConfig,
    CsvInputConfig,
    DeterminismConfig,
    DummyProviderConfig,
    FeatureFlagsConfig,
    HashingConfig,
    HttpClientConfig,
    HttpClientDefaults,
    HttpClientSettings,
    InterfaceFeaturesConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    PaginationConfig,
    PipelineConfig,
    ProviderConfigUnion,
    ProviderHttpConfig,
    QcConfig,
    QualityConfig,
    RuntimeConfig,
    StorageConfig,
    TransformConfig,
)
from bioetl.domain.configs.profile import ProfileConfig
from bioetl.domain.configs.sink import DataSinkConfig, OutputOptionsConfig
from bioetl.domain.configs.source import (
    CsvInputConfig as CsvInputConfigNew,
    DataSourceConfig as DataSourceConfigNew,
)

__all__ = [
    # Bounded context configs (new modular structure)
    "PipelineIdentityConfig",
    "DataSourceConfigNew",
    "DataSinkConfig",
    "OutputOptionsConfig",
    "CsvInputConfigNew",
    # Primary HTTP configuration (single source of truth)
    "HttpClientConfig",
    "ProviderHttpConfig",
    # Provider configs
    "BaseProviderConfig",
    "ChemblSourceConfig",
    "DummyProviderConfig",
    "ProviderConfigUnion",
    # Pipeline config
    "PipelineConfig",
    "RuntimeConfig",
    # Sub-configs
    "BusinessKeyConfig",
    "CanonicalizationConfig",
    "CsvInputConfig",
    "DeterminismConfig",
    "FeatureFlagsConfig",
    "HashingConfig",
    "InterfaceFeaturesConfig",
    "LoggingConfig",
    "MetricsConfig",
    "NormalizationConfig",
    "ObservabilityConfig",
    "PaginationConfig",
    "ProfileConfig",
    "QualityConfig",
    "QcConfig",
    "StorageConfig",
    "TransformConfig",
    # Defaults configs
    "ClientDefaultsConfig",
    "DefaultsConfig",
    "HashingDefaultsConfig",
    "HttpDefaultsConfig",
    "NetworkDefaultsConfig",
    "NetworkHttpDefaultsConfig",
    "NormalizationDefaultsConfig",
    "SourceDefaultsConfig",
    "SourcesDefaultsConfig",
    # Protocols
    "PipelineConfigLoaderProtocol",
    # DEPRECATED: Legacy aliases (will be removed in future versions)
    "ClientConfig",  # Use HttpClientConfig
    "HttpClientDefaults",  # Use HttpClientConfig
    "HttpClientSettings",  # Use ProviderHttpConfig
    "HTTP_CLIENT_DEFAULTS",  # Use HttpClientConfig()
]
