"""Bootstrap functions for lock components.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.noop_logger import NoOpLogger

if TYPE_CHECKING:
    from bioetl.application.services.lock_service import LockService

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Note: Uses MemoryLock which is the in-process lock implementation.
    Lock operations only affect the current process. For distributed
    scenarios, a Redis-based implementation would be needed.

    Returns:
        LockService configured for the current environment.
    """
    from bioetl.application.services.lock_service import LockService

    lock_port = MemoryLock()
    noop_logger = NoOpLogger()

    return LockService(lock_port=lock_port, logger=noop_logger)
