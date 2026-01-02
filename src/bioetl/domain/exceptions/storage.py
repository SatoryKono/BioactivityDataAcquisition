"""Storage-related exceptions.

These errors involve I/O operations with storage systems
(S3, Delta Lake, local filesystem).

Implements granular error classification for:
- Delta Lake operations (write conflicts, transactions, schema)
- Storage quota and capacity issues
- General I/O errors

See ADR-016 for error handling strategy.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType


class StorageError(RecoverableError):
    """Base exception for storage-related errors.

    These errors typically involve I/O operations and may be transient.
    """

    error_type = ErrorType.NETWORK_ERROR


class BucketNotFoundError(StorageError):
    """Raised when S3 bucket does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class UploadError(StorageError):
    """Raised when upload to S3 fails."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, key: str, reason: str) -> None:
        self.key = key
        self.reason = reason
        super().__init__(f"Failed to upload '{key}': {reason}")


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


def _build_schema_error_message(
    table: str, new_fields: set[str], removed_fields: set[str]
) -> str:
    """Build error message for schema evolution error."""
    parts = [f"Schema drift detected for '{table}'"]
    if new_fields:
        parts.append(f"new fields: {sorted(new_fields)}")
    if removed_fields:
        parts.append(f"removed fields: {sorted(removed_fields)}")
    return ", ".join(parts)


class SchemaEvolutionError(StorageError):
    """Raised when schema drift is detected and on_schema_mismatch='error'.

    This error indicates that the incoming records have different fields
    compared to the existing table schema.
    """

    error_type = ErrorType.SCHEMA_EVOLUTION

    def __init__(
        self,
        table: str,
        new_fields: set[str] | None = None,
        removed_fields: set[str] | None = None,
    ) -> None:
        self.table = table
        self.new_fields = new_fields or set()
        self.removed_fields = removed_fields or set()
        super().__init__(
            _build_schema_error_message(table, self.new_fields, self.removed_fields)
        )


class BronzeValidationError(StorageError):
    """Raised when Bronze layer input validation fails.

    This error indicates that records passed to BronzeWriter
    are not valid JSON bytes. Critical error that should stop
    the pipeline to prevent invalid data in Bronze layer.
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        record_index: int | None = None,
        original_error: str | None = None,
    ) -> None:
        """Initialize BronzeValidationError.

        Args:
            message: Description of the validation failure.
            record_index: Optional 0-based index of the invalid record.
            original_error: Optional original error message from JSON parser.
        """
        self.record_index = record_index
        self.original_error = original_error
        parts = [message]
        if record_index is not None:
            parts.append(f"record_index={record_index}")
        if original_error is not None:
            parts.append(f"error={original_error}")
        super().__init__(", ".join(parts))


# =============================================================================
# Delta Lake Specific Errors (Granular Classification)
# =============================================================================


class DeltaWriteConflictError(StorageError):
    """Raised when Delta Lake detects a concurrent write conflict.

    This occurs during ACID transactions when another process modified
    the same data partition. Typically recoverable via retry.

    See delta-rs documentation for conflict resolution strategies.
    """

    error_type = ErrorType.NETWORK_ERROR  # Recoverable

    def __init__(
        self,
        table_path: str,
        operation: str = "write",
        conflicting_version: int | None = None,
    ) -> None:
        """Initialize DeltaWriteConflictError.

        Args:
            table_path: Path to the Delta table.
            operation: Type of operation that failed (write, merge, delete).
            conflicting_version: Optional Delta version that caused conflict.
        """
        self.table_path = table_path
        self.operation = operation
        self.conflicting_version = conflicting_version
        msg = f"Delta write conflict on '{table_path}' during {operation}"
        if conflicting_version is not None:
            msg += f" (conflicting version: {conflicting_version})"
        super().__init__(msg)


class DeltaTransactionError(CriticalError):
    """Raised when Delta Lake transaction fails to commit.

    This is a critical error indicating transaction log corruption
    or unrecoverable state. Pipeline should fail to prevent data loss.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        table_path: str,
        reason: str,
        version: int | None = None,
    ) -> None:
        """Initialize DeltaTransactionError.

        Args:
            table_path: Path to the Delta table.
            reason: Description of why transaction failed.
            version: Optional Delta version where failure occurred.
        """
        self.table_path = table_path
        self.reason = reason
        self.version = version
        msg = f"Delta transaction failed on '{table_path}': {reason}"
        if version is not None:
            msg += f" (version: {version})"
        super().__init__(msg)


class DeltaSchemaValidationError(CriticalError):
    """Raised when schema validation fails during Delta write.

    This error indicates that incoming data doesn't match
    the expected Delta table schema in strict mode.

    See ADR-018 for Gold strict validation policy.
    """

    error_type = ErrorType.SCHEMA_MISMATCH_GOLD

    def __init__(
        self,
        table_path: str,
        expected_columns: list[str] | None = None,
        actual_columns: list[str] | None = None,
        type_mismatches: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        """Initialize DeltaSchemaValidationError.

        Args:
            table_path: Path to the Delta table.
            expected_columns: Expected column names.
            actual_columns: Actual column names in data.
            type_mismatches: Dict of column -> (expected_type, actual_type).
        """
        self.table_path = table_path
        self.expected_columns = expected_columns or []
        self.actual_columns = actual_columns or []
        self.type_mismatches = type_mismatches or {}

        parts = [f"Schema validation failed for '{table_path}'"]

        if expected_columns and actual_columns:
            missing = set(expected_columns) - set(actual_columns)
            extra = set(actual_columns) - set(expected_columns)
            if missing:
                parts.append(f"missing columns: {sorted(missing)}")
            if extra:
                parts.append(f"unexpected columns: {sorted(extra)}")

        if type_mismatches:
            mismatches = [
                f"{col}: expected {exp}, got {act}"
                for col, (exp, act) in type_mismatches.items()
            ]
            parts.append(f"type mismatches: [{', '.join(mismatches)}]")

        super().__init__(", ".join(parts))


class DeltaOptimizeError(StorageError):
    """Raised when Delta VACUUM or OPTIMIZE operation fails.

    These maintenance operations are recoverable and can be retried.
    Failed optimization doesn't affect data integrity.
    """

    error_type = ErrorType.NETWORK_ERROR  # Recoverable

    def __init__(
        self,
        table_path: str,
        operation: str,  # "vacuum" or "optimize"
        reason: str,
    ) -> None:
        """Initialize DeltaOptimizeError.

        Args:
            table_path: Path to the Delta table.
            operation: Type of maintenance operation.
            reason: Description of failure.
        """
        self.table_path = table_path
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Delta {operation} failed on '{table_path}': {reason}"
        )


class StorageQuotaExceededError(CriticalError):
    """Raised when storage quota or disk space is exhausted.

    This is a critical error requiring immediate operator attention.
    Pipeline cannot continue without freeing storage.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        path: str,
        quota_bytes: int | None = None,
        used_bytes: int | None = None,
    ) -> None:
        """Initialize StorageQuotaExceededError.

        Args:
            path: Storage path that exceeded quota.
            quota_bytes: Optional quota limit in bytes.
            used_bytes: Optional current usage in bytes.
        """
        self.path = path
        self.quota_bytes = quota_bytes
        self.used_bytes = used_bytes

        msg = f"Storage quota exceeded for '{path}'"
        if quota_bytes is not None and used_bytes is not None:
            msg += f" (used: {used_bytes:,} bytes, quota: {quota_bytes:,} bytes)"
        super().__init__(msg)
