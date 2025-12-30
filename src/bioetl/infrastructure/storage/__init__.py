"""Storage adapters for Bronze/Silver/Gold layers.

Implements RULES.md §2.1 - Medallion Architecture.

This package provides:
- Writers: BronzeWriter, SilverWriter, GoldWriter
- Utilities: RetentionManager (VACUUM, optimize, time travel)

Naming Convention (unified with Medallion layers):
- BronzeWriter - writes to Bronze layer (JSONL + zstd)
- SilverWriter - writes to Silver layer (Delta Lake)
- GoldWriter - writes to Gold layer (Delta Lake with SCD Type 2)

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
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.retention_manager import RetentionManager
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    "BronzeWriter",
    "BucketNotFoundError",
    "GoldWriter",
    "MergeConflictError",
    "RetentionManager",
    "SchemaViolationError",
    "SilverWriter",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
]
