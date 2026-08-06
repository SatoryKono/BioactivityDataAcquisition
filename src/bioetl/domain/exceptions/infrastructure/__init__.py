"""Deprecated compatibility facade for domain storage/platform exceptions.

Canonical import path (ARCH-REF-08 / #7709):
``bioetl.domain.exceptions.storage``.

This package remains a re-export surface so existing callers keep working.
New first-party code MUST import from ``domain.exceptions.storage``.
"""

from __future__ import annotations

from bioetl.domain.exceptions.storage import (
    BronzeValidationError,
    BucketNotFoundError,
    CachedBronzeEmptyError,
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    InfrastructureError,
    SchemaEvolutionError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    UploadError,
    _build_schema_error_message,
    _build_schema_validation_message,
    _format_column_diff,
    _format_type_mismatches,
)

__all__ = [
    "BronzeValidationError",
    "BucketNotFoundError",
    "CachedBronzeEmptyError",
    "DeltaOptimizeError",
    "DeltaSchemaValidationError",
    "DeltaTransactionError",
    "DeltaWriteConflictError",
    "InfrastructureError",
    "SchemaEvolutionError",
    "StorageError",
    "StorageQuotaExceededError",
    "TableNotFoundError",
    "UploadError",
    "_build_schema_error_message",
    "_build_schema_validation_message",
    "_format_column_diff",
    "_format_type_mismatches",
]
