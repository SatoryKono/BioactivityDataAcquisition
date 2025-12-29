"""Storage-related exceptions.

These errors involve I/O operations with storage systems
(S3, Delta Lake, local filesystem).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError
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
