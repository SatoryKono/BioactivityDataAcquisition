"""Domain layer exceptions.

Implements centralized exception hierarchy for all BioETL errors.
All exceptions should inherit from BioETLError to enable consistent error handling.

Each exception class defines an explicit `error_type` attribute for deterministic
error classification (see ErrorClassifier).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from bioetl.domain.types import ErrorType


class BioETLError(Exception):
    """Base exception for all BioETL errors.

    All exceptions in the system should inherit from this class to enable
    consistent error handling and classification.

    Attributes:
        error_type: Explicit ErrorType for deterministic classification.
                   Subclasses MUST override this attribute.
    """

    error_type: ClassVar[ErrorType]

    @classmethod
    def get_error_type(cls) -> ErrorType:
        """Get the error type for this exception class.

        Returns:
            ErrorType for this exception.

        Raises:
            AttributeError: If error_type is not defined (should not happen).
        """
        # Import here to avoid circular import at module load time
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)


class CriticalError(BioETLError):
    """Errors that should stop the pipeline immediately.

    These errors indicate serious problems that cannot be recovered from
    and require immediate attention. Examples: lock lost, data corruption,
    system resource exhaustion.
    """

    # Default for CriticalError subclasses that don't override
    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.DB_UNAVAILABLE)


class RecoverableError(BioETLError):
    """Errors that can be retried.

    These errors are typically transient and may succeed on retry.
    Examples: network timeouts, rate limits, temporary service unavailability.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.NETWORK_ERROR)


class DataQualityError(BioETLError):
    """Errors in data quality (skip record).

    These errors indicate problems with individual data records that should
    be logged and skipped, but should not stop the pipeline.
    Examples: schema violations, missing required fields, invalid data formats.
    """

    @classmethod
    def get_error_type(cls) -> ErrorType:
        from bioetl.domain.types import ErrorType

        return getattr(cls, "error_type", ErrorType.INVALID_DATA)


# ============================================================================
# Critical Errors
# ============================================================================


class LockLostError(CriticalError):
    """Raised when distributed lock is lost during execution.

    This is a CRITICAL error - worker MUST terminate before any commit.
    Losing the lock means another worker may have acquired it.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, run_id: str | None = None) -> None:
        self.key = key
        self.run_id = run_id
        msg = f"Lock lost: {key}"
        if run_id:
            msg += f" (run_id={run_id})"
        super().__init__(msg)


class LockAcquisitionError(CriticalError):
    """Raised when lock cannot be acquired.

    This prevents the pipeline from starting if the lock is held by another worker.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, current_owner: str | None = None) -> None:
        self.key = key
        self.current_owner = current_owner
        msg = f"Failed to acquire lock: {key}"
        if current_owner:
            msg += f" (owned by {current_owner})"
        super().__init__(msg)


class CheckpointConflictError(CriticalError):
    """Raised when checkpoint write fails due to concurrent modification.

    This indicates that another worker has modified the checkpoint,
    which could lead to data inconsistency.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, pipeline: str, message: str) -> None:
        self.pipeline = pipeline
        super().__init__(f"Checkpoint conflict in '{pipeline}': {message}")


class MergeConflictError(CriticalError):
    """Raised when Delta merge has conflicts.

    This indicates that the data merge operation has unresolved conflicts
    that require manual intervention.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table: str, conflicts: int) -> None:
        self.table = table
        self.conflicts = conflicts
        super().__init__(f"Merge conflict in '{table}': {conflicts} conflicts")


# ============================================================================
# Recoverable Errors
# ============================================================================


class RateLimitError(RecoverableError):
    """Raised when API rate limit is exceeded.

    The request should be retried after the specified delay.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.RATE_LIMIT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {provider}. Retry after {retry_after}s"
        )


class RetryExhaustedError(RecoverableError):
    """Raised when all retry attempts are exhausted.

    This indicates that a transient error persisted across all retry attempts.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self, url: str, attempts: int, last_error: Exception | None = None
    ) -> None:
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        msg = f"Exhausted {attempts} retry attempts for {url}"
        if last_error:
            msg += f": {last_error}"
        super().__init__(msg)


class CircuitBreakerOpenError(RecoverableError):
    """Raised when circuit breaker is open and blocking requests.

    This indicates that the service has failed repeatedly and the circuit breaker
    has opened to prevent further requests.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.TIMEOUT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {provider}. Retry after {retry_after}s"
        )


class ApiError(RecoverableError):
    """Raised when external API returns an error.

    This is a generic API error that may be retryable depending on the status code.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"[{status_code}] {message}"
        super().__init__(msg)


class ChemblApiError(ApiError):
    """Raised when ChEMBL API returns an error."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR


class StorageError(RecoverableError):
    """Base exception for storage-related errors.

    These errors typically involve I/O operations and may be transient.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR


class BucketNotFoundError(StorageError):
    """Raised when S3 bucket does not exist."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class UploadError(StorageError):
    """Raised when upload to S3 fails."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, key: str, reason: str) -> None:
        self.key = key
        self.reason = reason
        super().__init__(f"Failed to upload '{key}': {reason}")


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


# ============================================================================
# Data Quality Errors
# ============================================================================


class SchemaViolationError(DataQualityError):
    """Raised when data does not match expected schema.

    This indicates that a data record has schema validation errors and should be skipped.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.SCHEMA_VIOLATION

    def __init__(self, table: str, errors: list[str]) -> None:
        self.table = table
        self.errors = errors
        super().__init__(f"Schema validation failed for '{table}': {errors}")


class MissingRequiredFieldError(DataQualityError):
    """Raised when required field is missing from data record."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.MISSING_REQUIRED_FIELD

    def __init__(self, field: str, record_id: str | None = None) -> None:
        self.field = field
        self.record_id = record_id
        msg = f"Missing required field: {field}"
        if record_id:
            msg += f" (record_id={record_id})"
        super().__init__(msg)


class InvalidDataFormatError(DataQualityError):
    """Raised when data format is invalid."""

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.INVALID_DATA

    def __init__(self, field: str, value: str, expected_format: str) -> None:
        self.field = field
        self.value = value
        self.expected_format = expected_format
        super().__init__(
            f"Invalid format for '{field}': got '{value}', expected {expected_format}"
        )


class DataQualityThresholdError(BioETLError):
    """Raised when Data Quality error rate exceeds the hard threshold.

    This error indicates that the quality of the batch is too low to proceed,
    requiring the pipeline or batch to stop.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.DATA_QUALITY

    def __init__(self, error_rate: float, threshold: float) -> None:
        self.error_rate = error_rate
        self.threshold = threshold
        super().__init__(
            f"DQ Hard Threshold exceeded: {error_rate:.2%} errors (limit: {threshold:.2%})"
        )


# ============================================================================
# Authentication Errors
# ============================================================================


class AuthFailureError(CriticalError):
    """Raised when API authentication fails (401, 403).

    This is a CRITICAL error - pipeline should not continue without valid auth.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.AUTH_FAILURE

    def __init__(self, provider: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        msg = f"Authentication failed for {provider}"
        if status_code:
            msg += f" (HTTP {status_code})"
        super().__init__(msg)


class TimeoutError(RecoverableError):
    """Raised when request times out (502, 504, gateway errors).

    The request may be retried after a delay.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.TIMEOUT

    def __init__(self, message: str, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        msg = message
        if timeout_seconds:
            msg += f" (timeout: {timeout_seconds}s)"
        super().__init__(msg)


class NetworkError(RecoverableError):
    """Raised when network connectivity issues occur.

    This is a generic network error that may be retried.
    """

    from bioetl.domain.types import ErrorType

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)
