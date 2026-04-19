"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.

This package contains all port definitions organized by domain:
- storage: StoragePort for Medallion layer operations
- data_source: DataSourcePort, FilterableDataSourcePort for fetching
- observability: TracingPort, MetricsPort, LoggerPort, DQMonitorPort
- config: PipelineSettingsPort, SettingsPort, ConfigLoaderPort
- metadata: MetadataWriterPort, MetadataCoordinatorPort
- quality: DQ analysis, validation, quarantine, error handling
- runtime: Runner, checkpoint, locking, shutdown, memory, registry
- audit: AuditPort for write operation traceability
- resilience: RateLimiterPort, CircuitBreakerPort for fault tolerance
"""

from __future__ import annotations

from bioetl.domain.ports.adr import (
    AdrDocument,
    AdrInfo,
    AdrServicePort,
    AdrValidationIssue,
    AdrValidationReport,
)
from bioetl.domain.ports.audit import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    AuditPort,
)
from bioetl.domain.ports.config import (
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    SettingsLoaderPort,
    SettingsPort,
)
from bioetl.domain.ports.control_plane import (
    LineageStorePort,
    RunLedgerPort,
    RunManifestPort,
)
from bioetl.domain.ports.data_normalization import DataNormalizationPort
from bioetl.domain.ports.data_source import (
    DataSourceFactoryPort,
    DataSourcePort,
    FilterableDataSourcePort,
)
from bioetl.domain.ports.delta_reader import DeltaReaderPort
from bioetl.domain.ports.export import ExportCatalogPort, ExportWriterPort
from bioetl.domain.ports.filtering import InputFilterPort
from bioetl.domain.ports.health_check import (
    HealthCheckPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatePort,
    HealthStatusLiteral,
)
from bioetl.domain.ports.idmapping import IDMappingPort, IDMappingSourceReaderPort
from bioetl.domain.ports.metadata import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    SilverMetadataInput,
    SilverRef,
)
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    ExecutorMetricsPort,
    LoggerPort,
    MetricLabels,
    MetricsPort,
    MetricsPublisherPort,
    MetricsServerPort,
    TracingPort,
    resolve_metric_labels,
)
from bioetl.domain.ports.pii import PiiHasherPort
from bioetl.domain.ports.publication_strategy import (
    DataExtractorStrategy,
    IdentifierResolverStrategy,
    PublicationMetadataStrategy,
)
from bioetl.domain.ports.quality import (
    BronzeDQAnalyzerPort,
    BronzeDQConfigPort,
    ContractPolicyPort,
    DQReportWriterPort,
    ErrorClassifierPort,
    ErrorHandlerPort,
    FallbackPolicyPort,
    GoldDQAnalyzerPort,
    GoldDQConfigPort,
    GoldValidatorPort,
    QuarantinePort,
    QuarantineWriteRequest,
    SilverDQAnalyzerPort,
    SilverDQConfigPort,
    SilverValidatorPort,
)
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.runtime import (
    BatchIdGeneratorPort,
    BreakpointHit,
    CheckpointPort,
    ClockPort,
    CompositeCheckpointPort,
    DebugAction,
    ExecutionMetricsReadablePort,
    ExecutionMetricsRunnerPort,
    ExecutionObservabilityPort,
    LockPort,
    MemoryMonitorPort,
    MemoryStats,
    MetricsExtractorPort,
    PipelineDebugPort,
    PipelineFactoryPort,
    PipelineRegistryPort,
    PipelineSnapshot,
    RegistryAccessorPort,
    RunnablePort,
    RunnerFactoryPort,
    ShutdownPort,
    StageBreakpoint,
)
from bioetl.domain.ports.serialization import JsonEncoderPort
from bioetl.domain.ports.storage import (
    BronzeStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    SilverStoragePort,
    SilverWriteRequest,
    StorageLifecyclePort,
    StorageMaintenancePort,
    StoragePort,
)

__all__ = [
    "AdrDocument",
    "AdrInfo",
    "AdrServicePort",
    "AdrValidationIssue",
    "AdrValidationReport",
    "AuditEntry",
    "AuditLayer",
    "AuditOperation",
    "AuditPort",
    "BatchIdGeneratorPort",
    "BreakpointHit",
    "BronzeDQAnalyzerPort",
    "BronzeDQConfigPort",
    "BronzeMetadataInput",
    "BronzeStoragePort",
    "CheckpointPort",
    "CircuitBreakerPort",
    "ClockPort",
    "CompositeCheckpointPort",
    "ContractPolicyPort",
    "DQMonitorPort",
    "DQReportWriterPort",
    "DataExtractorStrategy",
    "DataNormalizationPort",
    "DataSourceFactoryPort",
    "DataSourcePort",
    "DebugAction",
    "DeltaReaderPort",
    "DomainConfigMapperPort",
    "ErrorClassifierPort",
    "ErrorHandlerPort",
    "ExecutionMetricsReadablePort",
    "ExecutionMetricsRunnerPort",
    "ExecutionObservabilityPort",
    "ExecutorMetricsPort",
    "ExportCatalogPort",
    "ExportWriterPort",
    "FallbackPolicyPort",
    "FilterableDataSourcePort",
    "GoldDQAnalyzerPort",
    "GoldDQConfigPort",
    "GoldMetadataInput",
    "GoldStoragePort",
    "GoldValidatorPort",
    "HealthCheckPort",
    "HealthCheckResult",
    "HealthMonitorPort",
    "HealthStatePort",
    "HealthStatusLiteral",
    "IDMappingPort",
    "IDMappingSourceReaderPort",
    "IdentifierResolverStrategy",
    "InputFilterPort",
    "JsonEncoderPort",
    "LineageStorePort",
    "LockPort",
    "LoggerPort",
    "MemoryMonitorPort",
    "MemoryStats",
    "MergedStoragePort",
    "MetadataCoordinatorPort",
    "MetadataWriterPort",
    "MetricLabels",
    "MetricsExtractorPort",
    "MetricsPort",
    "MetricsPublisherPort",
    "MetricsServerPort",
    "PiiHasherPort",
    "PipelineConfigLoaderPort",
    "PipelineDebugPort",
    "PipelineFactoryPort",
    "PipelineRegistryPort",
    "PipelineSettingsPort",
    "PipelineSnapshot",
    "PipelineYamlConfigPort",
    "PublicationMetadataStrategy",
    "QuarantinePort",
    "QuarantineWriteRequest",
    "RateLimiterPort",
    "RegistryAccessorPort",
    "RunLedgerPort",
    "RunManifestPort",
    "RunnablePort",
    "RunnerFactoryPort",
    "SettingsLoaderPort",
    "SettingsPort",
    "ShutdownPort",
    "SilverDQAnalyzerPort",
    "SilverDQConfigPort",
    "SilverMetadataInput",
    "SilverRef",
    "SilverWriteRequest",
    "SilverStoragePort",
    "SilverValidatorPort",
    "StageBreakpoint",
    "StorageLifecyclePort",
    "StorageMaintenancePort",
    "StoragePort",
    "TracingPort",
    "resolve_metric_labels",
]

_GENERIC_DISCOVERY_EXCLUDED_PORTS = frozenset({"RegistryAccessorPort"})


def __dir__() -> list[str]:
    """Keep generic facade discovery aligned with the tracked public port census."""
    return sorted(
        name for name in globals() if name not in _GENERIC_DISCOVERY_EXCLUDED_PORTS
    )
