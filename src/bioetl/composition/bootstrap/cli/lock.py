"""Bootstrap functions for lock CLI operations.

Contains bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

from bioetl.application.services.ops.lock_service import LockService
from bioetl.composition.bootstrap.cli.noop import create_noop_logger
from bioetl.composition.factories.services.port_factories import create_lock

__all__ = ["bootstrap_lock_service"]


def bootstrap_lock_service() -> LockService:
    """Bootstrap LockService for CLI lock management commands.

    Creates a LockService for administrative lock operations.
    Used by CLI for `lock release` and `lock list` commands.

    Uses the same lock port factory as runtime service wiring
    (:func:`create_lock`). Today that is the local in-process
    ``MemoryLock`` adapter; lock list/release therefore operate on the
    process-local lock table. A durable inter-process adapter is not yet
    part of the product surface — when one is introduced it must be
    registered through ``create_lock`` so CLI and runtime stay aligned.

    Returns:
        LockService configured for the current environment.
    """
    lock_port = create_lock()
    noop_logger = create_noop_logger()

    return LockService(lock_port=lock_port, logger=noop_logger)
