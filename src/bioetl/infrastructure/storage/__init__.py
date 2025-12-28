"""Storage adapters for Bronze/Silver/Gold layers.

Implements RULES.md §2.1 - Medallion Architecture.

This package provides:
- Writers: BronzeWriter, DeltaWriter (Silver), GoldWriter
- Utilities: RetentionManager (VACUUM, optimize, time travel), validate_lock_for_write
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
from bioetl.infrastructure.storage.lock_validator import validate_lock_for_write
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
    "validate_lock_for_write",
]
