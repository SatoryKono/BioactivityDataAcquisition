"""Locking port for distributed lock coordination.

This port provides a mechanism for coordinating operations across
multiple instances or processes, preventing race conditions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.types import RunID


@runtime_checkable
class LockPort(Protocol):
    """Port for distributed locking.

    This interface provides a mechanism for coordinating operations across
    multiple instances or processes, preventing race conditions.
    """

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """Acquire a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run attempting to acquire the lock.
            ttl: Time-to-live for the lock in seconds.
            wait: If True, wait for the lock to be released if it's already held.
            wait_timeout: Maximum time to wait for the lock in seconds.
            exclusive: If True, acquire an exclusive lock.

        Returns:
            True if the lock was acquired, False otherwise.
        """
        ...

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run releasing the lock.
            exclusive: If True, release an exclusive lock.

        Returns:
            True if the lock was released, False otherwise.
        """
        ...

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Refresh a lock's TTL to prevent it from expiring.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run refreshing the lock.
            exclusive: If True, refresh an exclusive lock.

        Returns:
            True if the heartbeat was successful, False otherwise.
        """
        ...

    async def validate_owner(
        self,
        key: str,
        owner_id: RunID,
    ) -> bool:
        """Validate that the given owner_id holds the lock.

        This is the Safety Guard: before writing to storage, the writer
        MUST validate that it still holds the lock. This prevents split-brain
        scenarios where the lock expired but the writer continued.

        Args:
            key: The unique key for the lock.
            owner_id: The ID of the run to validate.

        Returns:
            True if owner_id currently holds the lock, False otherwise.
        """
        ...

    async def aclose(self) -> None:
        """Gracefully close the lock connection and release resources."""
        ...
