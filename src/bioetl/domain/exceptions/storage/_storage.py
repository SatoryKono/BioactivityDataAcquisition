# Host attrs/methods provided by concrete composition.
"""Storage and schema-evolution exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError, RecoverableError
from bioetl.domain.types import ErrorType


class StorageError(RecoverableError):
    """Base exception for storage-related errors."""

    error_type = ErrorType.NETWORK_ERROR


class BucketNotFoundError(StorageError):
    """Raised when a storage bucket does not exist."""

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
    """Raised when an object upload fails."""

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
        return quota_bytes, used_bytes, reason, version  # type: ignore[return-value]  # pyright: ignore[reportReturnType]

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


class BronzeValidationError(StorageError):
    """Raised when Bronze payload validation fails."""

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
    """Raised when expected cached Bronze data is missing."""

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
        super().__init__(
            f"No Bronze data found for {provider}/{entity_type}{date_info}. "
            f"Searched path: {bronze_path}"
        )
