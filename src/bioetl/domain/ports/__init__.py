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
- normalization: UnitConverterPort, ValueValidatorPort, ActivityAggregatorPort
"""

from bioetl.domain.ports.audit import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    AuditPort,
)
from bioetl.domain.ports.checkpoint import CheckpointPort
from bioetl.domain.ports.data_source import (
    DataSourcePort,
    FilterableDataSourcePort,
    FilterableWithFallbackPort,
)
from bioetl.domain.ports.filtering import InputFilterPort, InputFilterWithFallbackPort
from bioetl.domain.ports.health_check import (
    HealthCheckPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatusLiteral,
)
from bioetl.domain.ports.locking import LockPort
from bioetl.domain.ports.memory import MemoryMonitorPort, MemoryStats
from bioetl.domain.ports.noop import (
    NoOpAudit,
    NoOpMemoryMonitor,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
)
from bioetl.domain.ports.normalization import (
    ActivityAggregatorPort,
    NormalizationServicePort,
    OutlierFilterPort,
    UnitConverterPort,
    ValueValidatorPort,
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
    "ActivityAggregatorPort",
    "AuditEntry",
    "AuditLayer",
    "AuditOperation",
    "AuditPort",
    "CheckpointPort",
    "CircuitBreakerPort",
    "DQMonitorPort",
    "DataSourcePort",
    "FilterableDataSourcePort",
    "FilterableWithFallbackPort",
    "GoldValidatorPort",
    "HealthCheckPort",
    "HealthCheckResult",
    "HealthMonitorPort",
    "HealthStatusLiteral",
    "InputFilterPort",
    "InputFilterWithFallbackPort",
    "JsonEncoderPort",
    "LockPort",
    "LoggerPort",
    "MemoryMonitorPort",
    "MemoryStats",
    "MetricsExtractorPort",
    "MetricsPort",
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetrics",
    "NoOpPiiHasher",
    "NoOpTracing",
    "NormalizationServicePort",
    "OutlierFilterPort",
    "PiiHasherPort",
    "QuarantinePort",
    "RateLimiterPort",
    "RunnablePort",
    "RunnerFactoryPort",
    "ShutdownPort",
    "SilverValidatorPort",
    "StoragePort",
    "TracingPort",
    "UnitConverterPort",
    "ValueValidatorPort",
]
