"""Infrastructure exceptions facade."""

from __future__ import annotations

from bioetl.domain.exceptions.infrastructure._base import InfrastructureError
from bioetl.domain.exceptions.infrastructure._delta import (
    DeltaOptimizeError,
    DeltaSchemaValidationError,
    DeltaTransactionError,
    DeltaWriteConflictError,
    _build_schema_validation_message,
    _format_column_diff,
    _format_type_mismatches,
)
from bioetl.domain.exceptions.infrastructure._storage import (
    BronzeValidationError,
    BucketNotFoundError,
    CachedBronzeEmptyError,
    SchemaEvolutionError,
    StorageError,
    StorageQuotaExceededError,
    TableNotFoundError,
    UploadError,
    _build_schema_error_message,
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
