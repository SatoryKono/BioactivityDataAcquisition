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
        parts = [f"Schema drift detected for '{table}'"]
        if self.new_fields:
            parts.append(f"new fields: {sorted(self.new_fields)}")
        if self.removed_fields:
            parts.append(f"removed fields: {sorted(self.removed_fields)}")
        super().__init__(", ".join(parts))
