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
    MetricsFactoryProtocol,
    MetricsService,
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
    "ExportServiceProtocol",
    "ForensicRunDiffServiceProtocol",
    "GoldMergedWriteProtocol",
    "HealthServiceProtocol",
    "HistoricalReplayClosureServiceProtocol",
    "HistoricalReplayCorpusServiceProtocol",
    "HistoricalReplayUniverseServiceProtocol",
    "LineageInspectionServiceProtocol",
    "LockServiceProtocol",
    "MetricsFactoryProtocol",
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
    "RegistryEntryProtocol",
    "RunManifestInspectionServiceProtocol",
    "SchemaBuilderProtocol",
    "SecretValueProviderProtocol",
    "SilverMergedWriteProtocol",
    "StorageContextProtocol",
    "StorageFactoryProtocol",
    "SupportAwareDataSourceCreatorProtocol",
    "VacuumServiceProtocol",
    "WorkflowInspectionServiceProtocol",
    "WorkflowMetricsFactoryProtocol",
]
