"""Application-layer port protocols (ADR-058).

Supported entry: ``bioetl.application.ports``.
"""

from __future__ import annotations

from bioetl.application.ports.control_plane import (
    ControlPlaneArtifactLifecycleStoreProtocol,
)
from bioetl.application.ports.dq import (
    ConfigurableDQMonitor,
    DQDetectorConfig,
    DQReportServiceFactoryProtocol,
)
from bioetl.application.ports.health import HealthServiceProtocol
from bioetl.application.ports.metrics import (
    MetricsFactoryProtocol,
    MetricsService,
    WorkflowMetricsFactoryProtocol,
)
from bioetl.application.ports.observability import ObservabilitySettingsProtocol
from bioetl.application.ports.pipeline import (
    BaseServicesFactoryProtocol,
    ContractPolicyLoaderProtocol,
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
    CompositeMergeStorageProtocol,
    CompositeRuntimeStorageProtocol,
    GoldMergedWriteProtocol,
    SilverMergedWriteProtocol,
    StorageContextProtocol,
    StorageFactoryProtocol,
)

__all__ = [
    "AdapterCreatorProtocol",
    "BaseServicesFactoryProtocol",
    "CompositeMergeStorageProtocol",
    "CompositeRuntimeStorageProtocol",
    "ConfigurableDQMonitor",
    "ContractPolicyLoaderProtocol",
    "ControlPlaneArtifactLifecycleStoreProtocol",
    "DQDetectorConfig",
    "DQReportServiceFactoryProtocol",
    "DataSourceCreatorProtocol",
    "GoldMergedWriteProtocol",
    "HealthServiceProtocol",
    "MetricsFactoryProtocol",
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
    "StorageContextProtocol",
    "StorageFactoryProtocol",
    "SupportAwareDataSourceCreatorProtocol",
    "WorkflowMetricsFactoryProtocol",
]
