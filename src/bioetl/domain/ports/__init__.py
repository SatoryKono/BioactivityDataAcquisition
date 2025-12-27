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
)
from bioetl.domain.ports.filtering import InputFilterPort
from bioetl.domain.ports.locking import LockPort
from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.quarantine import QuarantinePort
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.serialization import JsonEncoderPort
from bioetl.domain.ports.storage import StoragePort
from bioetl.domain.ports.validation import GoldValidatorPort

__all__ = [
    "AuditEntry",
    "AuditLayer",
    "AuditOperation",
    "AuditPort",
    "CheckpointPort",
    "CircuitBreakerPort",
    "DQMonitorPort",
    "DataSourcePort",
    "FilterableDataSourcePort",
    "GoldValidatorPort",
    "InputFilterPort",
    "JsonEncoderPort",
    "LockPort",
    "LoggerPort",
    "MetricsPort",
    "NoOpAudit",
    "NoOpMetrics",
    "NoOpTracing",
    "QuarantinePort",
    "RateLimiterPort",
    "StoragePort",
    "TracingPort",
]
