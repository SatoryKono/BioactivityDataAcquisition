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
from bioetl.domain.ports.data_normalization import DataNormalizationPort
from bioetl.domain.ports.data_source import (
    DataSourceFactoryPort,
    DataSourcePort,
    FilterableDataSourcePort,
)
from bioetl.domain.ports.delta_reader import DeltaReaderPort
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
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMemoryMonitor,
    NoOpMetadataWriter,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
)
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    ExecutorMetricsPort,
    LoggerPort,
    MetricLabels,
    MetricsPort,
    MetricsServerPort,
    TracingPort,
    resolve_metric_labels,
)
from bioetl.domain.ports.pii import PiiHasherPort
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
    SilverDQAnalyzerPort,
    SilverDQConfigPort,
    SilverValidatorPort,
)
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.runtime import (
    BatchIdGeneratorPort,
    CheckpointPort,
    ClockPort,
    LockPort,
    MemoryMonitorPort,
    MemoryStats,
    MetricsExtractorPort,
    PipelineFactoryPort,
    PipelineRegistryPort,
    RegistryAccessorPort,
    RunnablePort,
    RunnerFactoryPort,
    ShutdownPort,
)
from bioetl.domain.ports.serialization import JsonEncoderPort
from bioetl.domain.ports.storage import (
    BronzeStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    SilverStoragePort,
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
    "BronzeDQAnalyzerPort",
    "BronzeDQConfigPort",
    "BronzeMetadataInput",
    "BronzeStoragePort",
    "CheckpointPort",
    "CircuitBreakerPort",
    "ClockPort",
    "ContractPolicyPort",
    "DQMonitorPort",
    "DQReportWriterPort",
    "DataNormalizationPort",
    "DataSourceFactoryPort",
    "DataSourcePort",
    "DeltaReaderPort",
    "DomainConfigMapperPort",
    "ErrorClassifierPort",
    "ErrorHandlerPort",
    "ExecutorMetricsPort",
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
    "InputFilterPort",
    "JsonEncoderPort",
    "LockPort",
    "LoggerPort",
    "MemoryMonitorPort",
    "MemoryStats",
    "MergedStoragePort",
    "MetadataCoordinatorPort",
    "MetadataWriterPort",
    "MetricsExtractorPort",
    "MetricLabels",
    "MetricsPort",
    "MetricsServerPort",
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetadataWriter",
    "NoOpMetrics",
    "NoOpPiiHasher",
    "NoOpTracing",
    "PiiHasherPort",
    "PipelineConfigLoaderPort",
    "PipelineFactoryPort",
    "PipelineRegistryPort",
    "PipelineSettingsPort",
    "PipelineYamlConfigPort",
    "QuarantinePort",
    "RateLimiterPort",
    "RegistryAccessorPort",
    "RunnablePort",
    "RunnerFactoryPort",
    "SettingsLoaderPort",
    "SettingsPort",
    "ShutdownPort",
    "SilverDQAnalyzerPort",
    "SilverDQConfigPort",
    "SilverMetadataInput",
    "SilverRef",
    "SilverStoragePort",
    "SilverValidatorPort",
    "StorageLifecyclePort",
    "StorageMaintenancePort",
    "StoragePort",
    "TracingPort",
    "resolve_metric_labels",
]
