"""Core domain types for BioETL.

Implements RULES.md §1 - Domain Layer with pure types and value objects.
No I/O operations allowed (REQ-ARCH-003).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, NewType, Self, TypeAlias, TypedDict
from uuid import UUID

if TYPE_CHECKING:
    import pyarrow

# Type aliases for semantic clarity
RunID = NewType("RunID", UUID)
"""Unique identifier for a pipeline run (correlation ID)."""

EntityID = NewType("EntityID", str)
"""Business key for an entity (e.g., 'CHEMBL123', 'pubchem:2244')."""

ContentHash = NewType("ContentHash", str)
"""SHA256 hash of canonical record representation for versioning."""

BatchID = NewType("BatchID", UUID)
"""Unique identifier for a data batch."""

ArrowSchema: TypeAlias = "pyarrow.Schema"
"""PyArrow schema type alias.

Uses TYPE_CHECKING for type hints without runtime dependency on pyarrow
in the domain layer. At runtime, this is a pyarrow.Schema object.
"""


class BronzeRecord(TypedDict):
    """Untyped dictionary representing a raw record from source."""

    # We use NotRequired for dynamic fields, but TypedDict doesn't allow mixing optional/required well in old python
    # For now, we assume keys are strings and values Any
    # This is a marker type for clarity in signatures
    pass


class SilverRecord(TypedDict, total=False):
    """Normalized record for Silver layer."""

    entity_id: str
    content_hash: str
    # Other fields are dynamic based on entity type


@dataclass(frozen=True)
class Watermark:
    """Value object for checkpoint watermarks.

    Supports multiple representations:
    - Timestamp (datetime) for time-based incremental
    - Offset (int) for cursor-based pagination
    - ID (str) for entity-based watermarks
    """

    _value: str | datetime | int

    @classmethod
    def from_timestamp(cls, ts: datetime) -> Self:
        return cls(_value=ts)

    @classmethod
    def from_offset(cls, offset: int) -> Self:
        return cls(_value=offset)

    @classmethod
    def from_id(cls, entity_id: str) -> Self:
        return cls(_value=entity_id)

    def to_api_param(self) -> str:
        if isinstance(self._value, datetime):
            return self._value.isoformat()
        return str(self._value)

    @property
    def value(self) -> str | datetime | int:
        return self._value

    def __str__(self) -> str:
        return self.to_api_param()

    def __int__(self) -> int:
        if isinstance(self._value, int):
            return self._value
        try:
            return int(self._value)  # type: ignore
        except (ValueError, TypeError):
            # This might be risky if we assume it works, but useful for PubChem
            raise ValueError(f"Cannot convert Watermark value '{self._value}' to int")


class RunType(str, Enum):
    """Type of pipeline run (RULES.md §2.4).

    Determines merge priority: REBUILD > BACKFILL > INCREMENTAL
    """

    INCREMENTAL = "incremental"
    """Incremental load from last watermark."""

    BACKFILL = "backfill"
    """Historical data backfill for specific date range."""

    REBUILD = "rebuild"
    """Full rebuild of all data (highest priority)."""

    def priority(self) -> int:
        """Return numeric priority for conflict resolution."""
        priorities = {
            RunType.REBUILD: 3,
            RunType.BACKFILL: 2,
            RunType.INCREMENTAL: 1,
        }
        return priorities[self]


class DriftLevel(str, Enum):
    """Schema drift severity levels (RULES.md §2.2).

    - INFO: New optional fields appear
    - WARN: >3 new fields appear
    - CRITICAL: Required fields (ID) disappear
    """

    INFO = "INFO"
    """New optional fields detected (logged)."""

    WARN = "WARN"
    """Significant drift detected (>3 fields), requires review within 48h."""

    CRITICAL = "CRITICAL"
    """Critical drift (missing required fields), blocks pipeline."""


class HealthStatus(str, Enum):
    """Provider health status (RULES.md §3.5).

    State transitions:
    - HEALTHY → DEGRADED (1-2 errors)
    - DEGRADED → UNHEALTHY (≥3 errors)
    - UNHEALTHY → DEGRADED (1 successful health check)
    - DEGRADED → HEALTHY (0 errors for 5min)
    """

    HEALTHY = "HEALTHY"
    """Provider is operational (0 errors)."""

    DEGRADED = "DEGRADED"
    """Provider experiencing issues (1-2 errors). Timeout x2, batch_size ÷2."""

    UNHEALTHY = "UNHEALTHY"
    """Provider is down (≥3 errors). Pipeline paused, alert P2."""

    def to_metric_value(self) -> int:
        """Convert to numeric value for Prometheus metric."""
        return {
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.HEALTHY: 2,
        }[self]


class CircuitBreakerState(str, Enum):
    """Circuit breaker state (RULES.md §3.1.4).

    State machine:
    - CLOSED: Normal operation
    - OPEN: Service unavailable (5 consecutive errors)
    - HALF_OPEN: Testing recovery (1 probe request after timeout)
    """

    CLOSED = "CLOSED"
    """Circuit is closed, requests pass through."""

    OPEN = "OPEN"
    """Circuit is open, requests are blocked (failure threshold reached)."""

    HALF_OPEN = "HALF_OPEN"
    """Circuit is testing recovery (1 probe request allowed)."""

    def to_metric_value(self) -> int:
        """Convert to numeric value for Prometheus metric."""
        return {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.HALF_OPEN: 1,
            CircuitBreakerState.OPEN: 2,
        }[self]


class DataClassification(str, Enum):
    """Data sensitivity classification (RULES.md §5.4)."""

    PUBLIC = "PUBLIC"
    """Publicly available data, no restrictions."""

    INTERNAL = "INTERNAL"
    """Internal use only, not for public distribution."""

    RESTRICTED = "RESTRICTED"
    """Contains PII or sensitive data, requires encryption/hashing."""


class ErrorType(str, Enum):
    """Error classification (RULES.md §3.1.1).

    Determines pipeline behavior:
    - CRITICAL: Fail pipeline immediately
    - RECOVERABLE: Retry with exponential backoff
    - DATA_QUALITY: Log and skip record (quarantine)
    """

    # Critical errors (stop pipeline)
    AUTH_FAILURE = "AUTH_FAILURE"
    """API authentication failed (401, 403)."""

    SCHEMA_MISMATCH_GOLD = "SCHEMA_MISMATCH_GOLD"
    """Gold layer schema validation failed (strict mode)."""

    DB_UNAVAILABLE = "DB_UNAVAILABLE"
    """Database connection failed."""

    LOCK_LOST = "LOCK_LOST"
    """Distributed lock lost during execution."""

    # Recoverable errors (retry)
    RATE_LIMIT = "RATE_LIMIT"
    """API rate limit exceeded (429)."""

    TIMEOUT = "TIMEOUT"
    """Request timeout (502, 504)."""

    NETWORK_ERROR = "NETWORK_ERROR"
    """Network connectivity issue."""

    # Data quality errors (log + skip)
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    """Record failed schema validation."""

    INVALID_DATA = "INVALID_DATA"
    """Invalid data format (e.g., malformed SMILES)."""

    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    """Required field is missing or null."""

    DATA_QUALITY = "DATA_QUALITY"
    """General data quality error (e.g. thresholds)."""

    def is_critical(self) -> bool:
        """Check if error should fail pipeline."""
        return self in {
            ErrorType.AUTH_FAILURE,
            ErrorType.SCHEMA_MISMATCH_GOLD,
            ErrorType.DB_UNAVAILABLE,
            ErrorType.LOCK_LOST,
        }

    def is_recoverable(self) -> bool:
        """Check if error should be retried."""
        return self in {
            ErrorType.RATE_LIMIT,
            ErrorType.TIMEOUT,
            ErrorType.NETWORK_ERROR,
        }

    def is_data_quality(self) -> bool:
        """Check if error is data quality issue (skip record)."""
        return self in {
            ErrorType.SCHEMA_VIOLATION,
            ErrorType.INVALID_DATA,
            ErrorType.MISSING_REQUIRED_FIELD,
            ErrorType.DATA_QUALITY,
        }


class DQStatus(str, Enum):
    """Quarantine record status (RULES.md §2.6)."""

    NEW = "NEW"
    """Newly quarantined record, needs triage."""

    IGNORED = "IGNORED"
    """Reviewed and marked as non-actionable."""

    REPROCESSED = "REPROCESSED"
    """Successfully reprocessed and moved to Silver."""
