"""Storage and schema-evolution exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType


class StorageError(RecoverableError):
    """Base exception for storage-related errors."""

    error_type = ErrorType.NETWORK_ERROR


class BucketNotFoundError(StorageError):
    """Raised when S3 bucket does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        super().__init__(f"Bucket '{bucket}' not found")


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


class UploadError(StorageError):
    """Raised when upload to storage fails."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, key: str, reason: str) -> None:
        self.key = key
        self.reason = reason
        super().__init__(f"Failed to upload '{key}': {reason}")


class StorageQuotaExceededError(CriticalError):
    """Raised when storage quota or disk space is exhausted."""

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


def _build_schema_error_message(
    table: str,
    new_fields: set[str],
    removed_fields: set[str],
) -> str:
    """Build message for schema evolution mismatch."""
    parts = [f"Schema drift detected for '{table}'"]
    if new_fields:
        parts.append(f"new fields: {sorted(new_fields)}")
    if removed_fields:
        parts.append(f"removed fields: {sorted(removed_fields)}")
    return ", ".join(parts)


class SchemaEvolutionError(StorageError):
    """Raised when schema drift is detected and strict mode is enabled."""

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


class CachedBronzeEmptyError(StorageError):
    """Raised when cached Bronze data is requested but not found."""

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        provider: str,
        entity_type: str,
        bronze_path: str,
        date_filter: str | None = None,
    ) -> None:
        self.provider = provider
        self.entity_type = entity_type
        self.bronze_path = bronze_path
        self.date_filter = date_filter

        date_info = f" for date {date_filter}" if date_filter else ""
        message = (
            f"No Bronze data found for {provider}/{entity_type}{date_info}. "
            f"Searched path: {bronze_path}"
        )
        super().__init__(message)
