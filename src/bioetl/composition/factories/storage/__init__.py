"""Storage factory subpackage."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from bioetl.composition.factories.storage.bundle import StorageBundle
from bioetl.composition.factories.storage.factory import StorageContext, StorageFactory
from bioetl.composition.factories.storage.resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)

__all__ = [
    "StorageBundle",
    "StorageContext",
    "StorageFactory",
    "create_silver_atomic_retry_policy",
    "create_silver_merge_resilience_policy",
    "run_storage_blocking",
]


async def run_storage_blocking[T](call: Callable[[], T]) -> T:
    """Run a blocking storage callable off the event-loop thread."""
    return await asyncio.to_thread(call)
