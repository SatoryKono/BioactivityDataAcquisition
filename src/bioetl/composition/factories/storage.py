"""Storage Module for Bronze/Silver/Gold layers.

Consolidated module for storage infrastructure - provides backward-compatible
re-exports from the split modules.

The actual implementations are now in:
- storage_adapter.py: StorageAdapter class (~330 LOC)
- storage_factory.py: StorageFactory and StorageContext (~120 LOC)

This module re-exports all public symbols for backward compatibility.
Existing imports like `from bioetl.composition.factories.storage import StorageFactory`
will continue to work.

Split per docs/REFACTORING_PLAN.md [P3] Storage Factory Split.
"""

from __future__ import annotations

# Re-export from split modules for backward compatibility
from .storage_adapter import StorageAdapter
from .storage_factory import StorageContext, StorageFactory

__all__ = ["StorageAdapter", "StorageContext", "StorageFactory"]
