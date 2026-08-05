"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from bioetl.application.services.ops.lock_service import LockService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.infrastructure.locking.memory_lock import MemoryLock

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Note: Uses MemoryLock which is the in-process lock implementation.
    Lock operations only affect the current process. For inter-process
    scenarios, an external coordinator adapter would be required.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = MemoryLock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)
