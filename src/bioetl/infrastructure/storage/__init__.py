"""Storage adapters for Bronze/Silver/Gold layers.

Implements RULES.md §2.1 - Medallion Architecture.
"""

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

__all__ = [
    "BronzeWriter",
    "BucketNotFoundError",
    "DeltaWriter",
    "GoldWriter",
    "MergeConflictError",
    "SchemaViolationError",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
]
