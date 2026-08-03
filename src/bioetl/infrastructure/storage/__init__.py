"""Storage package utilities and shared exceptions.

Owner modules under ``bioetl.infrastructure.storage.*`` are the canonical import
targets for concrete Bronze/Silver/Gold writers and Delta helpers.
"""

from __future__ import annotations

from bioetl.domain.exceptions import (
    BucketNotFoundError,
    MergeConflictError,
    SchemaViolationError,
    StorageError,
    TableNotFoundError,
    UploadError,
)
from bioetl.infrastructure.storage.atomic import (
    AtomicWriteError,
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)
from bioetl.infrastructure.storage.bronze_write_result_helpers import (
    is_bronze_write_result_persisted,
)

__all__ = [
    "AtomicWriteError",
    "BucketNotFoundError",
    "MergeConflictError",
    "SchemaViolationError",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
    "atomic_write",
    "atomic_write_bytes",
    "atomic_write_text",
    "is_bronze_write_result_persisted",
]
