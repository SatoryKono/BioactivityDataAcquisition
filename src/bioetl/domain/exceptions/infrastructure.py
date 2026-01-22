"""Infrastructure and storage exceptions.

These errors involve storage systems, filesystems, and environment configuration.
Most are critical and should stop the pipeline.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType


def _format_column_diff(expected: list[str], actual: list[str]) -> list[str]:
    """Format missing and extra columns (private helper)."""
    parts: list[str] = []
    missing = set(expected) - set(actual)
    extra = set(actual) - set(expected)
    if missing:
        parts.append(f"missing columns: {sorted(missing)}")
    if extra:
        parts.append(f"unexpected columns: {sorted(extra)}")
    return parts


def _format_type_mismatches(mismatches: dict[str, tuple[str, str]]) -> str:
    """Format type mismatches (private helper)."""
    formatted = [
        f"{col}: expected {exp}, got {act}" for col, (exp, act) in mismatches.items()
    ]
    return f"type mismatches: [{', '.join(formatted)}]"


def _build_delta_schema_validation_message(
    table_path: str,
    expected_columns: list[str],
    actual_columns: list[str],
    type_mismatches: dict[str, tuple[str, str]],
) -> str:
    """Build error message for Delta schema validation error."""
    parts = [f"Schema validation failed for '{table_path}'"]

    if expected_columns and actual_columns:
        parts.extend(_format_column_diff(expected_columns, actual_columns))

    if type_mismatches:
        parts.append(_format_type_mismatches(type_mismatches))

    return ", ".join(parts)


class InfrastructureError(CriticalError):
    """Base class for infrastructure-level errors (storage, database, filesystem, configuration).

    These errors typically indicate environment or system issues that may require pipeline stoppage.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self, message: str, failed_components: list[str] | None = None
    ) -> None:
        self.failed_components = failed_components or []
        super().__init__(message)


class StorageError(InfrastructureError):
    """Base class for storage-related errors (I/O operations failures, etc.)."""

    error_type = ErrorType.NETWORK_ERROR  # Can be transient


class BucketNotFoundError(StorageError):
    """Raised when the specified storage bucket does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class TableNotFoundError(StorageError):
    """Raised when a required table or path in the data store is not found."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


class UploadError(StorageError):
    """Raised when a file or object upload to storage fails."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, key: str, reason: str) -> None:
        self.key = key
        self.reason = reason
        super().__init__(f"Failed to upload '{key}': {reason}")


class SchemaEvolutionError(StorageError):
    """Raised when an incoming data batch contains schema drift that is not allowed."""

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
        parts = [f"Schema drift detected for '{table}'"]
        if new_fields:
            parts.append(f"new fields: {sorted(new_fields)}")
        if removed_fields:
            parts.append(f"removed fields: {sorted(removed_fields)}")
        super().__init__(", ".join(parts))


class DeltaOptimizeError(StorageError):
    """Raised when a maintenance operation (e.g., vacuum or optimize) on a Delta Lake table fails."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        table_path: str,
        operation: str,  # "vacuum" or "optimize"
        reason: str,
    ) -> None:
        self.table_path = table_path
        self.operation = operation
        self.reason = reason
        super().__init__(f"Delta {operation} failed on '{table_path}': {reason}")


class LockAcquisitionError(InfrastructureError):
    """Raised when a distributed lock cannot be acquired."""

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, current_owner: str | None = None) -> None:
        self.key = key
        self.current_owner = current_owner
        msg = f"Failed to acquire lock: {key}"
        if current_owner:
            msg += f" (owned by {current_owner})"
        super().__init__(msg)


class LockLostError(InfrastructureError):
    """Raised when a held lock is lost during execution."""

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, run_id: str | None = None) -> None:
        self.key = key
        self.run_id = run_id
        msg = f"Lock lost: {key}"
        if run_id:
            msg += f" (run_id={run_id})"
        super().__init__(msg)


class CheckpointConflictError(InfrastructureError):
    """Raised when a pipeline checkpoint update fails due to concurrent modification."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, pipeline: str, message: str) -> None:
        self.pipeline = pipeline
        super().__init__(f"Checkpoint conflict in '{pipeline}': {message}")


class MergeConflictError(InfrastructureError):
    """Raised when a data merge operation encounters conflicts that cannot be auto-resolved."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table: str, conflicts: int) -> None:
        self.table = table
        self.conflicts = conflicts
        super().__init__(f"Merge conflict in '{table}': {conflicts} conflicts")


class DeltaTransactionError(InfrastructureError):
    """Raised when a Delta Lake transaction fails to commit."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        table_path: str,
        reason: str,
        version: int | None = None,
    ) -> None:
        self.table_path = table_path
        self.reason = reason
        self.version = version
        msg = f"Delta transaction failed on '{table_path}': {reason}"
        if version is not None:
            msg += f" (version: {version})"
        super().__init__(msg)


class StorageQuotaExceededError(InfrastructureError):
    """Raised when a storage quota or disk space limit is exceeded."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        path: str,
        quota_bytes: int | None = None,
        used_bytes: int | None = None,
    ) -> None:
        self.path = path
        self.quota_bytes = quota_bytes
        self.used_bytes = used_bytes

        msg = f"Storage quota exceeded for '{path}'"
        if quota_bytes is not None and used_bytes is not None:
            msg += f" (used: {used_bytes:,} bytes, quota: {quota_bytes:,} bytes)"
        super().__init__(msg)


class DeltaWriteConflictError(StorageError):
    """Raised when Delta Lake detects a concurrent write conflict."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        table_path: str,
        operation: str = "write",
        conflicting_version: int | None = None,
    ) -> None:
        self.table_path = table_path
        self.operation = operation
        self.conflicting_version = conflicting_version
        msg = f"Delta write conflict on '{table_path}' during {operation}"
        if conflicting_version is not None:
            msg += f" (conflicting version: {conflicting_version})"
        super().__init__(msg)


class BronzeValidationError(StorageError):
    """Raised when Bronze layer input validation fails."""

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        record_index: int | None = None,
        original_error: str | None = None,
    ) -> None:
        self.record_index = record_index
        self.original_error = original_error
        parts = [message]
        if record_index is not None:
            parts.append(f"record_index={record_index}")
        if original_error is not None:
            parts.append(f"error={original_error}")
        super().__init__(", ".join(parts))


class DeltaSchemaValidationError(InfrastructureError):
    """Raised when schema validation fails during Delta write (strict mode)."""

    error_type = ErrorType.SCHEMA_MISMATCH_GOLD

    def __init__(
        self,
        table_path: str,
        expected_columns: list[str] | None = None,
        actual_columns: list[str] | None = None,
        type_mismatches: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        self.table_path = table_path
        self.expected_columns = expected_columns or []
        self.actual_columns = actual_columns or []
        self.type_mismatches = type_mismatches or {}

        msg = _build_delta_schema_validation_message(
            table_path,
            self.expected_columns,
            self.actual_columns,
            self.type_mismatches,
        )
        super().__init__(msg)
