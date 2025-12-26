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
"""

from bioetl.domain.ports.checkpoint import CheckpointPort
from bioetl.domain.ports.data_source import (
    DataSourcePort,
    FilterableDataSourcePort,
)
from bioetl.domain.ports.filtering import InputFilterPort
from bioetl.domain.ports.locking import LockPort
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.quarantine import QuarantinePort
from bioetl.domain.ports.resilience import CircuitBreakerPort, RateLimiterPort
from bioetl.domain.ports.storage import StoragePort
from bioetl.domain.ports.validation import GoldValidatorPort

__all__ = [
    "CheckpointPort",
    "CircuitBreakerPort",
    "DQMonitorPort",
    "DataSourcePort",
    "FilterableDataSourcePort",
    "GoldValidatorPort",
    "InputFilterPort",
    "LockPort",
    "LoggerPort",
    "MetricsPort",
    "QuarantinePort",
    "RateLimiterPort",
    "StoragePort",
    "TracingPort",
]
