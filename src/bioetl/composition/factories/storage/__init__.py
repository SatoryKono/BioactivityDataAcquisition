"""Storage factory subpackage."""

from __future__ import annotations

from bioetl.composition.factories.storage.adapter import StorageAdapter
from bioetl.composition.factories.storage.factory import StorageContext, StorageFactory
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)

__all__ = [
    "StorageAdapter",
    "StorageContext",
    "StorageFactory",
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
]
