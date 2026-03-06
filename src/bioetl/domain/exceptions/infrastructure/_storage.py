"""Storage and schema-evolution exceptions."""

from __future__ import annotations

from typing import Any, cast

from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType


class StorageError(RecoverableError):
    """Base exception for storage-related errors."""

    error_type = ErrorType.NETWORK_ERROR


def BucketNotFoundError(bucket: str) -> StorageError:
    """Compatibility constructor for legacy BucketNotFoundError."""
    error = StorageError(f"Bucket '{bucket}' not found")
    error = cast(StorageError, error.with_context(bucket=bucket))
    cast(
        Any, error
    ).error_type = ErrorType.DB_UNAVAILABLE  # Any: legacy exception compatibility shim
    return error


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


def UploadError(key: str, reason: str) -> StorageError:
    """Compatibility constructor for legacy UploadError."""
    error = StorageError(f"Failed to upload '{key}': {reason}")
    error = cast(StorageError, error.with_context(key=key, reason=reason))
    cast(
        Any, error
    ).error_type = ErrorType.NETWORK_ERROR  # Any: legacy exception compatibility shim
    return error


class StorageQuotaExceededError(CriticalError):
    """Raised when storage quota or disk space is exhausted."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        path: str | None = None,
        quota_bytes: int | None = None,
        used_bytes: int | None = None,
        *,
        table_path: str | None = None,
        reason: str | None = None,
        version: int | None = None,
    ) -> None:
        if isinstance(quota_bytes, str) and reason is None:
            reason = quota_bytes
            quota_bytes = None
            if isinstance(used_bytes, int):
                version = used_bytes
                used_bytes = None

        resolved_path = table_path if table_path is not None else path
        if resolved_path is None:
            raise ValueError("path or table_path must be provided")
        path = resolved_path

        self.path = path
        self.table_path = path
        self.quota_bytes = quota_bytes
        self.used_bytes = used_bytes
        self.reason = reason
        self.version = version

        if reason is not None:
            msg = f"Delta transaction failed on '{path}': {reason}"
            if version is not None:
                msg += f" (version: {version})"
            super().__init__(msg)
            return

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


def BronzeValidationError(
    message: str,
    record_index: int | None = None,
    original_error: str | None = None,
) -> StorageError:
    """Compatibility constructor for legacy BronzeValidationError."""
    parts = [message]
    if record_index is not None:
        parts.append(f"record_index={record_index}")
    if original_error is not None:
        parts.append(f"error={original_error}")
    error = StorageError(", ".join(parts))
    error = cast(
        StorageError,
        error.with_context(
            record_index=record_index,
            original_error=original_error,
        ),
    )
    cast(
        Any, error
    ).error_type = ErrorType.INVALID_DATA  # Any: legacy exception compatibility shim
    return error


def CachedBronzeEmptyError(
    provider: str,
    entity_type: str,
    bronze_path: str,
    date_filter: str | None = None,
) -> StorageError:
    """Compatibility constructor for legacy CachedBronzeEmptyError."""
    date_info = f" for date {date_filter}" if date_filter else ""
    message = (
        f"No Bronze data found for {provider}/{entity_type}{date_info}. "
        f"Searched path: {bronze_path}"
    )
    error = StorageError(message)
    error = cast(
        StorageError,
        error.with_context(
            provider=provider,
            entity_type=entity_type,
            bronze_path=bronze_path,
            date_filter=date_filter,
        ),
    )
    cast(
        Any, error
    ).error_type = ErrorType.INVALID_DATA  # Any: legacy exception compatibility shim
    return error
