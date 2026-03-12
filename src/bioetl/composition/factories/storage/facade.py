"""Storage compatibility-only facade for Bronze/Silver/Gold wiring.

Provides backward-compatible re-exports from the split storage modules.

The actual implementations are now in:
- storage_adapter.py: StorageAdapter class (~330 LOC)
- storage_factory.py: StorageFactory and StorageContext (~120 LOC)

This module exists to preserve legacy import paths only. New first-party code
should import canonical modules directly instead of introducing new usages here.

Split per docs/REFACTORING_PLAN.md [P3] Storage Factory Split.
"""

from __future__ import annotations

# Re-export writers for test patching compatibility
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

# Re-export from split modules for backward compatibility
from .adapter import StorageAdapter
from .factory import StorageContext, StorageFactory

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
]
