"""Application-layer port protocols (ADR-058).

Supported entry: ``bioetl.application.ports``.
"""

from bioetl.application.ports.control_plane import (
    ControlPlaneArtifactLifecycleStoreProtocol,
)
from bioetl.application.ports.dq import (
    ConfigurableDQMonitor,
    DQDetectorConfig,
    DQReportServiceFactory,
)
from bioetl.application.ports.metrics import (
    MetricsFactory,
    MetricsService,
    WorkflowMetricsFactory,
)
from bioetl.application.ports.observability import ObservabilitySettingsProtocol
from bioetl.application.ports.pipeline import (
    BaseServicesFactoryProtocol,
    ContractPolicyLoader,
    PipelineRunnerProtocol,
    RegistryEntryProtocol,
    SchemaBuilderProtocol,
)
from bioetl.application.ports.pipeline_registry import PipelineRegistryProtocol
from bioetl.application.ports.providers import (
    AdapterCreatorProtocol,
    DataSourceCreatorProtocol,
    ProviderAdapterFactoryProtocol,
    ProviderDataSourceAccessProtocol,
    ProviderHttpClientFactoryProtocol,
    ProviderRegistrarProtocol,
    ProviderSettingsProtocol,
    SecretValueProviderProtocol,
    SupportAwareDataSourceCreatorProtocol,
)
from bioetl.application.ports.storage import (
    CompositeMergeStorage,
    CompositeRuntimeStorageProtocol,
    GoldMergedWriteProtocol,
    SilverMergedWriteProtocol,
    StorageContextLike,
    StorageFactoryProtocol,
)

__all__ = [
    "AdapterCreatorProtocol",
    "BaseServicesFactoryProtocol",
    "CompositeMergeStorage",
    "CompositeRuntimeStorageProtocol",
    "ConfigurableDQMonitor",
    "ContractPolicyLoader",
    "ControlPlaneArtifactLifecycleStoreProtocol",
    "DQDetectorConfig",
    "DQReportServiceFactory",
    "DataSourceCreatorProtocol",
    "GoldMergedWriteProtocol",
    "MetricsFactory",
    "MetricsService",
    "ObservabilitySettingsProtocol",
    "PipelineRegistryProtocol",
    "PipelineRunnerProtocol",
    "ProviderAdapterFactoryProtocol",
    "ProviderDataSourceAccessProtocol",
    "ProviderHttpClientFactoryProtocol",
    "ProviderRegistrarProtocol",
    "ProviderSettingsProtocol",
    "RegistryEntryProtocol",
    "SchemaBuilderProtocol",
    "SecretValueProviderProtocol",
    "SilverMergedWriteProtocol",
    "StorageContextLike",
    "StorageFactoryProtocol",
    "SupportAwareDataSourceCreatorProtocol",
    "WorkflowMetricsFactory",
]
