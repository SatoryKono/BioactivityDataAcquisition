"""Domain enumerations for BioETL (pure domain, no I/O)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "CellularityType",
    "CircuitBreakerState",
    "DataClassification",
    "DriftLevel",
    "ErrorType",
    "ExecutionContext",
    "HealthStatus",
    "PublicationType",
    "QuarantineRecordStatus",
    "RunType",
]


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
    """Runtime lock ownership lost during execution."""

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

    Persisted status of quarantine records (uppercase for backward compat).
    Distinct from QuarantineStatus (domain lifecycle) and DQEvaluationStatus.
    """

    NEW = "NEW"
    """Newly quarantined record, needs triage."""

    IGNORED = "IGNORED"
    """Reviewed and marked as non-actionable."""

    REPROCESSED = "REPROCESSED"
    """Successfully reprocessed and moved to Silver."""
