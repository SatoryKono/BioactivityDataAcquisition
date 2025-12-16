"""Storage layer exceptions.

DEPRECATED: This module is deprecated. Use bioetl.domain.exceptions instead.
All exceptions have been moved to the domain layer for centralized error handling.

This module now re-exports exceptions from domain for backward compatibility.
"""

# Import from domain and re-export for backward compatibility
from bioetl.domain.exceptions import (
    BucketNotFoundError,
    MergeConflictError,
    SchemaViolationError as SchemaValidationError,
    StorageError,
    TableNotFoundError,
    UploadError,
)

__all__ = [
    "StorageError",
    "BucketNotFoundError",
    "UploadError",
    "SchemaValidationError",
    "TableNotFoundError",
    "MergeConflictError",
]
