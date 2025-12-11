"""Domain configuration models (pure, without I/O).

Deprecated aliases (will be removed in v3.0):
    - ClientConfig -> use HttpClientConfig
    - HttpClientSettings -> use ProviderHttpConfig
    - HttpClientDefaults -> use HttpClientConfig
    - HTTP_CLIENT_DEFAULTS -> use HttpClientConfig()
    - QcConfig -> use QualityControlConfig

These deprecated names are available via lazy loading with DeprecationWarning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Deprecated aliases are loaded lazily via __getattr__ to emit warnings
# Import _compat module names for documentation purposes
from bioetl.domain.configs._compat import __all__ as _COMPAT_ALL
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
from bioetl.domain.configs.normalization import NormalizationConfig

# ConfigMigrator is now loaded lazily via __getattr__ with deprecation warning
# as it has been moved to infrastructure layer
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
    TransformConfig,
)
from bioetl.domain.configs.profile import ProfileConfig

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
    # Migration utilities
    "ConfigMigrator",
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
    # DEPRECATED: Legacy aliases (will be removed in v3.0)
    # These are lazy-loaded with DeprecationWarning via __getattr__
    "ClientConfig",  # Use HttpClientConfig
    "HttpClientDefaults",  # Use HttpClientConfig
    "HttpClientSettings",  # Use ProviderHttpConfig
    "HTTP_CLIENT_DEFAULTS",  # Use HttpClientConfig()
    "QcConfig",  # Use QualityControlConfig
]


def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for lazy loading deprecated aliases.

    Delegates to _compat module which handles deprecation warnings.
    Also handles ConfigMigrator which was moved to infrastructure layer.
    """
    if name == "ConfigMigrator":
        import warnings
        from bioetl.domain.configs.migration import ConfigMigrator

        warnings.warn(
            "Importing ConfigMigrator from bioetl.domain.configs is deprecated. "
            "Import from bioetl.infrastructure.config.migration instead. "
            "This re-export will be removed in a future release.",
            DeprecationWarning,
            stacklevel=2,
        )
        return ConfigMigrator

    if name in _COMPAT_ALL:
        from bioetl.domain.configs import _compat

        return getattr(_compat, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For static type checking only
if TYPE_CHECKING:
    from bioetl.domain.configs._compat import (
        HTTP_CLIENT_DEFAULTS as HTTP_CLIENT_DEFAULTS,
        ClientConfig as ClientConfig,
        HttpClientDefaults as HttpClientDefaults,
        HttpClientSettings as HttpClientSettings,
        QcConfig as QcConfig,
    )
