"""Application-layer port protocols (ADR-058).

Supported entry: ``bioetl.application.ports``.
"""

from __future__ import annotations

from bioetl.application.ports.control_plane import (
    ControlPlaneArtifactLifecycleStoreProtocol,
    ForensicRunDiffServiceProtocol,
    HistoricalReplayClosureServiceProtocol,
    HistoricalReplayCorpusServiceProtocol,
    HistoricalReplayUniverseServiceProtocol,
    LineageInspectionServiceProtocol,
    RunManifestInspectionServiceProtocol,
    WorkflowInspectionServiceProtocol,
)
from bioetl.application.ports.dq import (
    ConfigurableDQMonitor,
    DQDetectorConfig,
    DQReportServiceFactoryProtocol,
)
from bioetl.application.ports.health import HealthServiceProtocol
from bioetl.application.ports.metrics import (
    DeleteResult,
    MetricsFactoryProtocol,
    MetricsServerStatus,
    MetricsService,
    PushResult,
    StartResult,
    WorkflowMetricsFactoryProtocol,
)
from bioetl.application.ports.observability import ObservabilitySettingsProtocol
from bioetl.application.ports.operations import (
    AuditInspectionServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    LockServiceProtocol,
    ObservabilityWorkflowServiceProtocol,
    VacuumServiceProtocol,
)
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
    HttpConfig,
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
    "AuditInspectionServiceProtocol",
    "BaseServicesFactoryProtocol",
    "CheckpointServiceProtocol",
    "CompositeMergeStorageProtocol",
    "CompositeRuntimeStorageProtocol",
    "ConfigServiceProtocol",
    "ConfigurableDQMonitor",
    "ContractMigrationServiceProtocol",
    "ContractPolicyLoaderProtocol",
    "ControlPlaneArtifactLifecycleStoreProtocol",
    "DQDetectorConfig",
    "DQReportServiceFactoryProtocol",
    "DataSourceCreatorProtocol",
    "DeleteResult",
    "ExportServiceProtocol",
    "ForensicRunDiffServiceProtocol",
    "GoldMergedWriteProtocol",
    "HealthServiceProtocol",
    "HistoricalReplayClosureServiceProtocol",
    "HistoricalReplayCorpusServiceProtocol",
    "HistoricalReplayUniverseServiceProtocol",
    "HttpConfig",
    "LineageInspectionServiceProtocol",
    "LockServiceProtocol",
    "MetricsFactoryProtocol",
    "MetricsServerStatus",
    "MetricsService",
    "ObservabilitySettingsProtocol",
    "ObservabilityWorkflowServiceProtocol",
    "PipelineRegistryProtocol",
    "PipelineRunnerProtocol",
    "ProviderAdapterFactoryProtocol",
    "ProviderDataSourceAccessProtocol",
    "ProviderHttpClientFactoryProtocol",
    "ProviderRegistrarProtocol",
    "ProviderSettingsProtocol",
    "PushResult",
    "RegistryEntryProtocol",
    "RunManifestInspectionServiceProtocol",
    "SchemaBuilderProtocol",
    "SecretValueProviderProtocol",
    "SilverMergedWriteProtocol",
    "StartResult",
    "StorageContextProtocol",
    "StorageFactoryProtocol",
    "SupportAwareDataSourceCreatorProtocol",
    "VacuumServiceProtocol",
    "WorkflowInspectionServiceProtocol",
    "WorkflowMetricsFactoryProtocol",
]
