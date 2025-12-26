"""Core domain types for BioETL.

Implements RULES.md §1 - Domain Layer with pure types and value objects.
No I/O operations allowed (REQ-ARCH-003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, NewType, TypeAlias, TypedDict
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


class RunType(str, Enum):
    """Type of pipeline run (RULES.md §2.4).

    Determines merge priority: REBUILD > BACKFILL > INCREMENTAL
    """

    INCREMENTAL = "incremental"
    """Incremental load."""

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

    SCHEMA_EVOLUTION = "SCHEMA_EVOLUTION"
    """Schema drift detected in Silver layer (new/removed fields)."""

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
            ErrorType.SCHEMA_EVOLUTION,
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


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of record validation.

    Attributes:
        valid: True if validation passed.
        errors: List of validation errors (empty if valid=True).
    """

    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConfigValidationError:
    """Single configuration validation error.

    Used by PreflightService to report Medallion invariant violations.

    Attributes:
        field: Configuration field path that failed validation.
        expected: Expected value or constraint description.
        actual: Actual value found in configuration.
        rule: Reference to RULES.md section defining this constraint.
    """

    field: str
    expected: str
    actual: str
    rule: str


@dataclass(frozen=True, slots=True)
class ComponentHealthResult:
    """Result of a single component health check.

    Attributes:
        component: Name of the component (e.g., 'storage', 'data_source').
        status: Health status of the component.
        duration_seconds: Time taken to perform the health check.
        error_message: Optional error message if check failed.
    """

    component: str
    status: HealthStatus
    duration_seconds: float
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated health check report.

    Attributes:
        results: List of individual component health results.
        checked_at: Timestamp when checks were performed.
    """

    results: list[ComponentHealthResult]
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def is_healthy(self) -> bool:
        """Return True if all critical components are healthy."""
        return all(r.status != HealthStatus.UNHEALTHY for r in self.results)

    @property
    def overall_status(self) -> HealthStatus:
        """Return worst status among all components."""
        if not self.results:
            return HealthStatus.HEALTHY

        statuses = [r.status for r in self.results]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def get_failures(self) -> list[ComponentHealthResult]:
        """Return list of components with UNHEALTHY status."""
        return [r for r in self.results if r.status == HealthStatus.UNHEALTHY]
