"""Storage and schema-evolution exceptions."""

from __future__ import annotations

from typing import cast

from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType


class StorageError(RecoverableError):
    """Base exception for storage-related errors."""

    error_type = ErrorType.NETWORK_ERROR


def bucket_not_found_error(bucket: str) -> StorageError:
    """Compatibility constructor for legacy BucketNotFoundError.

    Args:
        bucket: Name of the missing storage bucket.

    Returns:
        StorageError with DB_UNAVAILABLE type and bucket context attached.
    """
    error = StorageError(f"Bucket '{bucket}' not found")
    error = cast(StorageError, error.with_context(bucket=bucket))
    error.error_type = ErrorType.DB_UNAVAILABLE  # type: ignore[misc]  # instance override of ClassVar
    return error


class TableNotFoundError(StorageError):
    """Raised when Delta table does not exist."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table_path: str) -> None:
        self.table_path = table_path
        super().__init__(f"Table not found: '{table_path}'")


def upload_error(key: str, reason: str) -> StorageError:
    """Compatibility constructor for legacy UploadError.

    Args:
        key: Storage key or path of the object that failed to upload.
        reason: Human-readable description of the upload failure.

    Returns:
        StorageError with NETWORK_ERROR type and upload context attached.
    """
    error = StorageError(f"Failed to upload '{key}': {reason}")
    error = cast(StorageError, error.with_context(key=key, reason=reason))
    error.error_type = ErrorType.NETWORK_ERROR  # type: ignore[misc]  # instance override of ClassVar
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
        """Initialise a ``StorageQuotaExceededError`` or Delta transaction failure.

        The constructor handles two distinct usage modes via backward-compatible
        argument overloading:

        1. **Quota exceeded** — provide ``path``/``table_path``, ``quota_bytes`` and
           ``used_bytes`` to report a disk/quota limit breach.
        2. **Delta transaction failure** — provide ``table_path`` and ``reason``
           (e.g. a concurrent-write conflict message) plus an optional ``version``.

        A legacy positional-argument form (``quota_bytes`` as string, ``used_bytes``
        as version integer) is detected at runtime and re-mapped transparently.

        Args:
            path: File-system path of the affected storage location. Used when
                ``table_path`` is not provided.
            quota_bytes: Storage quota limit in bytes; ``None`` when reporting a
                Delta transaction failure rather than a quota breach.
            used_bytes: Bytes consumed at the time of the error; ``None`` when
                reporting a Delta transaction failure.
            table_path: Keyword-only alternative to ``path``; takes precedence over
                ``path`` when both are supplied.
            reason: Human-readable description of a Delta transaction failure;
                mutually exclusive with quota-breach mode.
            version: Optional Delta table version number included in the error message
                when ``reason`` is provided.

        Raises:
            ValueError: If neither ``path`` nor ``table_path`` is provided.
        """
        quota_bytes, used_bytes, reason, version = self._normalize_legacy_args(
            quota_bytes,
            used_bytes,
            reason,
            version,
        )
        resolved = self._resolve_path(path, table_path)

        self.path = resolved
        self.table_path = resolved
        self.quota_bytes = quota_bytes
        self.used_bytes = used_bytes
        self.reason = reason
        self.version = version

        super().__init__(
            self._build_message(resolved, reason, version, quota_bytes, used_bytes)
        )

    @staticmethod
    def _normalize_legacy_args(
        quota_bytes: int | str | None,
        used_bytes: int | None,
        reason: str | None,
        version: int | None,
    ) -> tuple[int | None, int | None, str | None, int | None]:
        """Re-map legacy positional form where quota_bytes is a reason string."""
        if isinstance(quota_bytes, str) and reason is None:
            reason = quota_bytes
            quota_bytes = None
            if isinstance(used_bytes, int):
                version = used_bytes
                used_bytes = None
        return quota_bytes, used_bytes, reason, version  # type: ignore[return-value]

    @staticmethod
    def _resolve_path(path: str | None, table_path: str | None) -> str:
        """Resolve effective path, preferring table_path over path."""
        resolved = table_path if table_path is not None else path
        if resolved is None:
            raise ValueError("path or table_path must be provided")
        return resolved

    @staticmethod
    def _build_message(
        path: str,
        reason: str | None,
        version: int | None,
        quota_bytes: int | None,
        used_bytes: int | None,
    ) -> str:
        """Build the human-readable error message."""
        if reason is not None:
            msg = f"Delta transaction failed on '{path}': {reason}"
            if version is not None:
                msg += f" (version: {version})"
            return msg
        msg = f"Storage quota exceeded for '{path}'"
        if quota_bytes is not None and used_bytes is not None:
            msg += f" (used: {used_bytes:,} bytes, quota: {quota_bytes:,} bytes)"
        return msg


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


def bronze_validation_error(
    message: str,
    record_index: int | None = None,
    original_error: str | None = None,
) -> StorageError:
    """Compatibility constructor for legacy BronzeValidationError.

    Args:
        message: Primary error message describing the validation failure.
        record_index: Optional index of the offending record; defaults to None.
        original_error: Optional original exception message string; defaults to None.

    Returns:
        StorageError with INVALID_DATA type and validation context attached.
    """
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
    error.error_type = ErrorType.INVALID_DATA  # type: ignore[misc]  # instance override of ClassVar
    return error


def cached_bronze_empty_error(
    provider: str,
    entity_type: str,
    bronze_path: str,
    date_filter: str | None = None,
) -> StorageError:
    """Compatibility constructor for legacy CachedBronzeEmptyError.

    Args:
        provider: Provider name whose cached Bronze data was not found.
        entity_type: Entity type whose cached Bronze data was not found.
        bronze_path: Path that was searched for Bronze data.
        date_filter: Optional date filter that was applied; defaults to None.

    Returns:
        StorageError indicating that no Bronze data was found for the given context.
    """
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
    error.error_type = ErrorType.INVALID_DATA  # type: ignore[misc]  # instance override of ClassVar
    return error


BucketNotFoundError = bucket_not_found_error
UploadError = upload_error
BronzeValidationError = bronze_validation_error
CachedBronzeEmptyError = cached_bronze_empty_error
