"""Storage adapters for Bronze/Silver/Gold layers.

Implements RULES.md §2.1 - Medallion Architecture.

This package provides:
- Writers: BronzeWriter, SilverWriter, GoldWriter
- Utilities: RetentionPolicy (VACUUM, optimize, time travel)

Naming Convention (unified with Medallion layers):
- BronzeWriter - writes to Bronze layer (JSONL + zstd)
- SilverWriter - writes to Silver layer (Delta Lake)
- GoldWriter - writes to Gold layer (Delta Lake with SCD Type 2)

Note:
    Lock validation is now performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
"""

from __future__ import annotations

from importlib import import_module

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

# Backward-compatible package alias for tests/tools that patch
# `bioetl.infrastructure.storage.delta.*` via string import paths.
from . import delta as delta

_LAZY_EXPORTS = {
    "BronzeWriter": "bioetl.infrastructure.storage.bronze_writer",
    "DeltaReader": "bioetl.infrastructure.storage.delta_reader",
    "GoldWriter": "bioetl.infrastructure.storage.gold_writer",
    "RetentionPolicy": "bioetl.infrastructure.storage.support.retention",
    "SilverWriter": "bioetl.infrastructure.storage.silver_writer",
    "SilverForeignKeyReconciliationAdapter": (
        "bioetl.infrastructure.storage.workflow_foreign_key_reconciliation"
    ),
}


def __getattr__(name: str) -> object:
    """Lazily load heavy storage exports to avoid import-time Delta dependencies."""
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = [
    "AtomicWriteError",
    "BronzeWriter",
    "BucketNotFoundError",
    "DeltaReader",
    "GoldWriter",
    "MergeConflictError",
    "RetentionPolicy",
    "SchemaViolationError",
    "SilverForeignKeyReconciliationAdapter",
    "SilverWriter",
    "StorageError",
    "TableNotFoundError",
    "UploadError",
    "atomic_write",
    "atomic_write_bytes",
    "atomic_write_text",
    "delta",
    "is_bronze_write_result_persisted",
]
