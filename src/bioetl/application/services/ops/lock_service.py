"""Lock service for administrative operations (Application layer).

Provides high-level lock management for CLI and other interfaces.
Uses LockPort for actual lock operations.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = ["LockInfo", "LockService"]


import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LockPort, LoggerPort
    from bioetl.domain.types import RunID


@dataclass(frozen=True, slots=True)
class LockInfo:
    """Information about a held lock.

    Attributes:
        key: Lock key (typically pipeline name).
        owner_id: Run ID that holds the lock.
        exclusive: Whether this is an exclusive lock.
    """

    key: str
    owner_id: str
    exclusive: bool


@dataclass
class LockService:
    """Service for administrative lock operations.

    Provides high-level operations for lock management
    used by CLI and other interfaces. Wraps LockPort
    for Application-layer abstraction.

    Note: The current LockPort interface doesn't support
    listing all locks. This service provides what's possible
    with the current port interface.

    Attributes:
        lock_port: Port for lock operations.
        logger: Structured logger for observability.

    Example:
        >>> service = LockService(lock_port=port, logger=logger)
        >>> released = await service.release_lock("chembl_activity", run_id)
        >>> logger.info("lock_released", pipeline="chembl_activity", released=released)
    """

    lock_port: LockPort
    logger: LoggerPort

    async def check_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
    ) -> bool:
        """Check if a specific lock is held by the given owner.

        Args:
            pipeline_id: Pipeline identifier (lock key).
            owner_id: Run ID to check.

        Returns:
            True if the lock is held by this owner, False otherwise.
        """
        self.logger.debug(
            "Checking lock",
            pipeline=pipeline_id,
            owner_id=str(owner_id),
        )

        # Use validate_owner to check if lock is held
        is_held = await self.lock_port.validate_owner(
            key=pipeline_id,
            owner_id=owner_id,
        )

        self.logger.info(
            "Lock check complete",
            pipeline=pipeline_id,
            is_held=is_held,
        )

        return is_held

    async def release_lock(
        self,
        pipeline_id: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock for a specific pipeline.

        Args:
            pipeline_id: Pipeline identifier (lock key).
            owner_id: Run ID that holds the lock.
            exclusive: Whether this is an exclusive lock.

        Returns:
            True if lock was released, False if it wasn't held.
        """
        self.logger.info(
            "Releasing lock",
            pipeline=pipeline_id,
            owner_id=str(owner_id),
            exclusive=exclusive,
        )

        released = await self.lock_port.release(
            key=pipeline_id,
            owner_id=owner_id,
            exclusive=exclusive,
        )

        if released:
            self.logger.info(
                "Lock released",
                pipeline=pipeline_id,
            )
        else:
            self.logger.warning(
                "Lock not released (not held or already released)",
                pipeline=pipeline_id,
            )

        return released

    async def force_release_all(
        self,
        owner_id: RunID,
        pipeline_ids: list[str],
    ) -> list[str]:
        """Attempt to release locks for multiple pipelines.

        This is useful for cleanup after a crashed process.
        Only releases locks that are actually held by the given owner.

        Args:
            owner_id: Run ID that should hold the locks.
            pipeline_ids: List of pipeline identifiers to try releasing.

        Returns:
            List of pipeline IDs where locks were successfully released.
        """
        self.logger.info(
            "Force releasing locks",
            owner_id=str(owner_id),
            pipeline_count=len(pipeline_ids),
        )

        released: list[str] = []

        for pipeline_id in pipeline_ids:
            # Try both regular and exclusive locks
            if await self.release_lock(
                pipeline_id, owner_id, exclusive=False
            ) or await self.release_lock(pipeline_id, owner_id, exclusive=True):
                released.append(pipeline_id)

        self.logger.info(
            "Force release complete",
            released_count=len(released),
            released=released,
        )

        return released

    async def list_locks(self) -> list[LockInfo]:
        """List all currently held locks.

        Note: The current LockPort interface doesn't support
        listing all locks. This method returns an empty list
        and logs a warning. Future implementations may extend
        the LockPort to support this operation.

        Returns:
            List of LockInfo for all held locks (currently empty).
        """
        await asyncio.sleep(0)
        self.logger.warning(
            "list_locks not supported by current LockPort implementation",
            note="Returning empty list - port extension required",
        )

        # LockPort doesn't support listing locks
        # Would need to extend the port interface for this functionality
        return []

    async def aclose(self) -> None:
        """Close the service and release resources."""
        await self.lock_port.aclose()
