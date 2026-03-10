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
from bioetl.domain.ports.checkpoint import CheckpointPort
from bioetl.domain.ports.clock import ClockPort
from bioetl.domain.ports.data_normalization import DataNormalizationPort
from bioetl.domain.ports.data_source import (
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
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.pii import PiiHasherPort
from bioetl.domain.ports.quarantine import QuarantinePort
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.runner import (
    MetricsExtractorPort,
    RunnablePort,
    RunnerFactoryPort,
)
from bioetl.domain.ports.serialization import JsonEncoderPort
from bioetl.domain.ports.shutdown import ShutdownPort
from bioetl.domain.ports.storage import StoragePort
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
    "BronzeDQAnalyzerPort",
    "BronzeDQConfigPort",
    "BronzeMetadataInput",
    "CheckpointPort",
    "CircuitBreakerPort",
    "ClockPort",
    "DQMonitorPort",
    "DQReportWriterPort",
    "DataNormalizationPort",
    "DataSourcePort",
    "DeltaReaderPort",
    "FilterableDataSourcePort",
    "GoldDQAnalyzerPort",
    "GoldDQConfigPort",
    "GoldMetadataInput",
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
    "MetadataCoordinatorPort",
    "MetadataWriterPort",
    "MetricsExtractorPort",
    "MetricsPort",
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetadataWriter",
    "NoOpMetrics",
    "NoOpPiiHasher",
    "NoOpTracing",
    "PiiHasherPort",
    "QuarantinePort",
    "RateLimiterPort",
    "RunnablePort",
    "RunnerFactoryPort",
    "ShutdownPort",
    "SilverDQAnalyzerPort",
    "SilverDQConfigPort",
    "SilverMetadataInput",
    "SilverRef",
    "SilverValidatorPort",
    "StoragePort",
    "TracingPort",
]
