"""Legacy compatibility layer for config models."""

from bioetl.domain.configs.pipeline import (
    BaseProviderConfig,
    BusinessKeyConfig,
    CanonicalizationConfig,
    ChemblSourceConfig,
    CsvInputConfig,
    DeterminismConfig,
    DummyProviderConfig,
    FeatureFlagsConfig,
    HashingConfig,
    HttpClientConfig,
    InterfaceFeaturesConfig,
    LoggingConfig,
    MetricsConfig,
    NormalizationConfig,
    ObservabilityConfig,
    PaginationConfig,
    PipelineConfig,
    ProviderConfigUnion,
    ProviderHttpConfig,
    QualityConfig,
    QualityControlConfig,
    RuntimeConfig,
    StorageConfig,
)

# Legacy aliases for backward compatibility
ClientConfig = HttpClientConfig
HttpClientSettings = ProviderHttpConfig

__all__ = [
    "BaseProviderConfig",
    "BusinessKeyConfig",
    "CanonicalizationConfig",
    "ChemblSourceConfig",
    "CsvInputConfig",
    "DeterminismConfig",
    "DummyProviderConfig",
    "FeatureFlagsConfig",
    "HashingConfig",
    "HttpClientConfig",
    "InterfaceFeaturesConfig",
    "LoggingConfig",
    "MetricsConfig",
    "NormalizationConfig",
    "ObservabilityConfig",
    "PaginationConfig",
    "PipelineConfig",
    "ProviderConfigUnion",
    "ProviderHttpConfig",
    "QualityConfig",
    "QualityControlConfig",
    "RuntimeConfig",
    "StorageConfig",
    # DEPRECATED: Legacy aliases
    "ClientConfig",  # Use HttpClientConfig
    "HttpClientSettings",  # Use ProviderHttpConfig
]
