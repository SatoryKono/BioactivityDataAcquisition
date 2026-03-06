"""Core domain types for BioETL.

Implements RULES.md §1 - Domain Layer with pure types and value objects.
No I/O operations are allowed (REQ-ARCH-003).

Type Safety: NewType for IDs, TypedDict for records, frozen dataclasses for VOs.
See RULES.md §1.3 for Any usage justification (external APIs, logging, protocols).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, NewType, TypeAlias, TypedDict
from uuid import UUID

from bioetl.domain.types_config_validation import ConfigValidationError

if TYPE_CHECKING:
    import pandera as _pa
    import pyarrow

__all__ = [
    "BatchID",
    "CellularityType",
    "CircuitBreakerState",
    "ComponentHealthResult",
    "ConfigValidationError",
    "ContentHash",
    "DataClassification",
    "DriftLevel",
    "EntityID",
    "ErrorType",
    "ExecutionContext",
    "HealthReport",
    "HealthStatus",
    "JsonDict",
    "PreflightReport",
    "PublicationType",
    "QuarantineRecordStatus",
    "RunID",
    "RunType",
    "SilverRecord",
    "ValidationResult",
]


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
"""PyArrow schema type alias (runtime: pyarrow.Schema, import-time: string)."""

JsonDict: TypeAlias = dict[str, Any]  # Any: JSON payloads have heterogeneous values
"""Type alias for JSON-like dictionaries with string keys and heterogeneous values.

Use instead of ``dict[str, Any]`` for data originating from external APIs,
configuration files (YAML/JSON), or any other untyped key-value mapping.
Reduces visual type-debt while preserving semantic clarity.
"""

BronzeRecord: TypeAlias = JsonDict  # raw API JSON has heterogeneous values
"""Untyped dictionary representing a raw record from the source."""

GoldRecord: TypeAlias = JsonDict  # heterogeneous scalar types before Pandera coercion
"""Record after Silver→Gold transform, before schema validation."""

MetaDict: TypeAlias = JsonDict  # freeform metadata (str|int|float|datetime|None)
"""Freeform metadata bag used in aggregates, audit entries, events."""

ScdConfig: TypeAlias = dict[str, str]
"""SCD2 configuration mapping (column-role → column-name). Values are always str."""

GoldSchemaType: TypeAlias = "type[_pa.DataFrameModel]"
"""Pandera DataFrameModel class (not instance). TYPE_CHECKING-only at import time."""

PrimaryId: TypeAlias = str | int
"""Primary identifier extracted from a Bronze record (e.g., ChEMBL ID string or numeric ID)."""


class SilverRecord(TypedDict, total=False):
    """Normalized record for Silver layer."""

    entity_id: str
    content_hash: str
    # Other fields are dynamic based on entity type


class CellularityType(StrEnum):
    """Organism cellularity classification for assay context.

    Classifies organisms into three categories based on cellular organization:
    - ACELLULAR: viruses, phages (no cellular structure)
    - UNICELLULAR: bacteria, archaea, protists, yeasts
    - MULTICELLULAR: animals, plants, filamentous fungi
    """

    ACELLULAR = "acellular"
    UNICELLULAR = "unicellular"
    MULTICELLULAR = "multicellular"


class PublicationType(StrEnum):
    """Canonical publication type (kebab-case). See PUBLICATION_TYPE_MAPPING."""

    JOURNAL_ARTICLE = "journal-article"
    BOOK = "book"
    DATASET = "dataset"
    PATENT = "patent"
    REVIEW = "review"
    LETTER = "letter"
    EDITORIAL = "editorial"
    CLINICAL_TRIAL = "clinical-trial"
    META_ANALYSIS = "meta-analysis"
    CASE_REPORTS = "case-reports"
    COMPARATIVE_STUDY = "comparative-study"
    EVALUATION_STUDY = "evaluation-study"
    BOOK_CHAPTER = "book-chapter"
    PROCEEDINGS_ARTICLE = "proceedings-article"
    POSTED_CONTENT = "posted-content"
    REPORT = "report"
    STANDARD = "standard"
    DISSERTATION = "dissertation"
    PREPRINT = "preprint"
    OTHER = "other"


class ExecutionContext(StrEnum):
    """Execution context: how a pipeline is launched.

    Controls DQ severity resolution via ``FieldValidation.severity_enricher``.
    """

    ISOLATED = "isolated"
    ENRICHER = "enricher"
    DEPENDENCY = "dependency"

    @property
    def is_enricher(self) -> bool:
        """True when severity_enricher overrides should apply."""
        return self == ExecutionContext.ENRICHER


class RunType(StrEnum):
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
        """Return numeric priority for conflict resolution.

        Returns:
            Computed integer value.
        """
        priorities = {
            RunType.REBUILD: 3,
            RunType.BACKFILL: 2,
            RunType.INCREMENTAL: 1,
        }
        return priorities[self]


class DriftLevel(StrEnum):
    """Schema drift severity levels (RULES.md §2.2).

    - INFO: New optional fields appear
    - CRITICAL: Required fields (ID) disappear
    """

    INFO = "INFO"
    """New optional fields detected (logged)."""

    CRITICAL = "CRITICAL"
    """Critical drift (missing required fields), blocks pipeline."""


class HealthStatus(StrEnum):
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
        """Convert to numeric value for Prometheus metric.

        Returns:
            Computed integer value.
        """
        return {
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.HEALTHY: 2,
        }[self]


class CircuitBreakerState(StrEnum):
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
        """Convert to numeric value for Prometheus metric.

        Returns:
            Computed integer value.
        """
        return {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.HALF_OPEN: 1,
            CircuitBreakerState.OPEN: 2,
        }[self]


class DataClassification(StrEnum):
    """Data sensitivity classification (RULES.md §5.4)."""

    PUBLIC = "PUBLIC"
    """Publicly available data, no restrictions."""

    INTERNAL = "INTERNAL"
    """Internal use only, not for public distribution."""

    RESTRICTED = "RESTRICTED"
    """Contains PII or sensitive data, requires encryption/hashing."""


class ErrorType(StrEnum):
    """Error classification (RULES.md §3.1.1).

    Determines pipeline behavior:
    - CRITICAL: Fail the pipeline immediately
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
        """Check if error should fail the pipeline.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {
            ErrorType.AUTH_FAILURE,
            ErrorType.SCHEMA_MISMATCH_GOLD,
            ErrorType.DB_UNAVAILABLE,
            ErrorType.SCHEMA_EVOLUTION,
            ErrorType.LOCK_LOST,
        }

    def is_recoverable(self) -> bool:
        """Check if error should be retried.

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {
            ErrorType.RATE_LIMIT,
            ErrorType.TIMEOUT,
            ErrorType.NETWORK_ERROR,
        }

    def is_data_quality(self) -> bool:
        """Check if error is data quality issue (skip record).

        Returns:
            True if the condition is met, False otherwise.
        """
        return self in {
            ErrorType.SCHEMA_VIOLATION,
            ErrorType.INVALID_DATA,
            ErrorType.MISSING_REQUIRED_FIELD,
            ErrorType.DATA_QUALITY,
        }


class QuarantineRecordStatus(StrEnum):
    """Status of a quarantine record in Delta Lake storage (RULES.md §2.6).

    This enum represents the persisted status of quarantine records.
    Values are uppercase for backward compatibility with existing data.

    Note:
        This is distinct from:
        - QuarantineStatus in aggregates/quarantine_entry.py (domain lifecycle)
        - DQEvaluationStatus in value_objects/dq_result.py (DQ threshold checks)

    Attributes:
        NEW: Newly quarantined record, needs triage.
        IGNORED: Reviewed and marked as non-actionable.
        REPROCESSED: Successfully reprocessed and moved to Silver.
    """

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
        """Return list of components with UNHEALTHY status.

        Returns:
            Failures.
        """
        return [r for r in self.results if r.status == HealthStatus.UNHEALTHY]


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Preflight validation report.

    Aggregates results from infrastructure health checks and
    medallion policy validation.

    Attributes:
        health_report: Infrastructure health check results.
        medallion_policy_valid: True if config is compatible with policy.
        config_errors: List of configuration validation errors.
        checked_at: Timestamp when validation was performed.
    """

    health_report: HealthReport
    medallion_policy_valid: bool
    config_errors: list[ConfigValidationError] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def is_valid(self) -> bool:
        """Return True if all validations passed."""
        return self.health_report.is_healthy and self.medallion_policy_valid

    @property
    def should_block_startup(self) -> bool:
        """Return True if validation failures should block pipeline startup."""
        return not self.medallion_policy_valid or not self.health_report.is_healthy
