"""Domain configuration models (pure, without I/O)."""

from __future__ import annotations

from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol

# Bounded context configs
from bioetl.domain.configs.data_flow import DataFlowConfig
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
from bioetl.domain.configs.execution import ExecutionConfig
from bioetl.domain.configs.identity import PipelineIdentityConfig
from bioetl.domain.configs.manifest import PipelineManifest
from bioetl.domain.configs.pipeline import (
    BaseProviderConfig,
    BusinessKeyConfig,
    CanonicalizationConfig,
    ChemblSourceConfig,
    CsvInputConfig,
    DataSinkConfig,
    DataSourceConfig,
    DeterminismConfig,
    DummyProviderConfig,
    FeatureFlagsConfig,
    HashingConfig,
    HttpClientConfig,
    InterfaceFeaturesConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    OutputOptionsConfig,
    PaginationConfig,
    PipelineConfig,
    PipelineStagesConfig,
    ProviderConfigUnion,
    ProviderHttpConfig,
    QualityConfig,
    QualityControlConfig,
    RuntimeConfig,
    StorageConfig,
)
from bioetl.domain.configs.pipeline_options import (
    NormalizationConfig,
    ProfileConfig,
    TransformConfig,
)

__all__ = [
    # Bounded context configs (new modular structure)
    "PipelineIdentityConfig",
    "DataFlowConfig",
    "ExecutionConfig",
    "PipelineManifest",
    "DataSourceConfig",
    "DataSinkConfig",
    "OutputOptionsConfig",
    "CsvInputConfig",
    "PipelineStagesConfig",
    # Execution aggregate (groups stages + runtime + transform)
    "ExecutionConfig",
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
    "QualityControlConfig",
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
]
