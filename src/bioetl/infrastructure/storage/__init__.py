"""Storage adapters for Bronze/Silver/Gold layers.

Implements RULES.md §2.1 - Medallion Architecture.

This package provides:
- Writers: BronzeWriter, DeltaWriter (Silver), GoldWriter
- Utilities: RetentionManager (VACUUM, optimize, time travel)

Note:
    Lock validation is now performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
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
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.retention_manager import RetentionManager

__all__ = [
    "BronzeWriter",
    "BucketNotFoundError",
    "DeltaWriter",
    "GoldWriter",
    "MergeConflictError",
    "RetentionManager",
    "SchemaViolationError",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
]
