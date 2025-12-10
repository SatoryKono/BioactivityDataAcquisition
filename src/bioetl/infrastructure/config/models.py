"""
Backward-compat layer exposing config models from domain package.

Tests and legacy code import from ``bioetl.infrastructure.config.models``; keep
these re-exports in sync with ``bioetl.domain.configs``.
"""

from bioetl.domain.configs import (  # noqa: F401
    HTTP_CLIENT_DEFAULTS,
    BaseProviderConfig,
    BusinessKeyConfig,
    CanonicalizationConfig,
    ChemblSourceConfig,
    ClientConfig,
    CsvInputConfig,
    DefaultsConfig,
    DeterminismConfig,
    DummyProviderConfig,
    FeatureFlagsConfig,
    HashingConfig,
    HashingDefaultsConfig,
    HttpClientConfig,
    HttpClientDefaults,
    HttpClientSettings,
    HttpDefaultsConfig,
    InterfaceFeaturesConfig,
    LoggingConfig,
    MetricsConfig,
    NetworkDefaultsConfig,
    NetworkHttpDefaultsConfig,
    NormalizationConfig,
    NormalizationDefaultsConfig,
    ObservabilityConfig,
    PaginationConfig,
    PipelineConfig,
    ProfileConfig,
    ProviderConfigUnion,
    ProviderHttpConfig,
    QcConfig,
    QualityConfig,
    RuntimeConfig,
    SourceDefaultsConfig,
    SourcesDefaultsConfig,
    StorageConfig,
)

__all__ = [
    # Primary HTTP configuration
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
    # Defaults configs
    "DefaultsConfig",
    "HashingDefaultsConfig",
    "HttpDefaultsConfig",
    "NetworkDefaultsConfig",
    "NetworkHttpDefaultsConfig",
    "NormalizationDefaultsConfig",
    "SourceDefaultsConfig",
    "SourcesDefaultsConfig",
    # DEPRECATED: Legacy aliases
    "ClientConfig",  # Use HttpClientConfig
    "HttpClientDefaults",  # Use HttpClientConfig
    "HttpClientSettings",  # Use ProviderHttpConfig
    "HTTP_CLIENT_DEFAULTS",  # Use HttpClientConfig()
]
