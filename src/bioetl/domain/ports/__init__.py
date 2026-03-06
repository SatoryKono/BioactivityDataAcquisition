"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.

This package contains all port definitions organized by domain:
- storage: StoragePort for Medallion layer operations
- data_source: DataSourcePort, FilterableDataSourcePort for fetching
- locking: LockPort for distributed locking
- checkpoint: CheckpointPort for pipeline state
- quarantine: QuarantinePort for failed records
- observability: TracingPort, MetricsPort, LoggerPort, DQMonitorPort
- validation: GoldValidatorPort for Gold layer validation
- filtering: InputFilterPort for CSV filter loading
- resilience: RateLimiterPort, CircuitBreakerPort for fault tolerance
- serialization: JsonEncoderPort for JSON encoding
- audit: AuditPort for write operation traceability
- shutdown: ShutdownPort for graceful termination coordination
- memory: MemoryMonitorPort for adaptive batch sizing
- data_normalization: DataNormalizationPort for text/data normalization
- delta_reader: DeltaReaderPort for read-only Delta table access
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
from bioetl.domain.ports.batch_id import BatchIdGeneratorPort
from bioetl.domain.ports.checkpoint import CheckpointPort
from bioetl.domain.ports.clock import ClockPort
from bioetl.domain.ports.config_loader_port import (
    DomainConfigMapperPort,
    PipelineConfigLoaderPort,
    SettingsLoaderPort,
)
from bioetl.domain.ports.config_port import (
    PipelineSettingsPort,
    PipelineYamlConfigPort,
    SettingsPort,
)
from bioetl.domain.ports.contract_policy import ContractPolicyPort
from bioetl.domain.ports.data_normalization import DataNormalizationPort
from bioetl.domain.ports.data_source import (
    DataSourceFactoryPort,
    DataSourcePort,
    FilterableDataSourcePort,
)
from bioetl.domain.ports.delta_reader import DeltaReaderPort
from bioetl.domain.ports.dq_config import (
    BronzeDQConfigPort,
    GoldDQConfigPort,
    SilverDQConfigPort,
)
from bioetl.domain.ports.dq_report import (
    BronzeDQAnalyzerPort,
    DQReportWriterPort,
    GoldDQAnalyzerPort,
    SilverDQAnalyzerPort,
)
from bioetl.domain.ports.error_classifier import ErrorClassifierPort
from bioetl.domain.ports.error_handler import ErrorHandlerPort
from bioetl.domain.ports.fallback_policy import FallbackPolicyPort
from bioetl.domain.ports.filtering import InputFilterPort
from bioetl.domain.ports.health_check import (
    HealthCheckPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatePort,
    HealthStatusLiteral,
)
from bioetl.domain.ports.idmapping import IDMappingPort, IDMappingSourceReaderPort
from bioetl.domain.ports.locking import LockPort
from bioetl.domain.ports.memory import MemoryMonitorPort, MemoryStats
from bioetl.domain.ports.metadata import MetadataWriterPort
from bioetl.domain.ports.metadata_coordinator import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinatorPort,
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
    MetricsPort,
    MetricsServerPort,
    TracingPort,
)
from bioetl.domain.ports.pii import PiiHasherPort
from bioetl.domain.ports.quarantine import QuarantinePort
from bioetl.domain.ports.registry_port import (
    PipelineRegistryPort,
    RegistryAccessorPort,
)
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.runner import (
    MetricsExtractorPort,
    PipelineFactoryPort,
    RunnablePort,
    RunnerFactoryPort,
)
from bioetl.domain.ports.serialization import JsonEncoderPort
from bioetl.domain.ports.shutdown import ShutdownPort
from bioetl.domain.ports.storage import (
    BronzeStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
    StoragePort,
)
from bioetl.domain.ports.validation import GoldValidatorPort, SilverValidatorPort

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
]
