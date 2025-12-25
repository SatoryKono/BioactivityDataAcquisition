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
