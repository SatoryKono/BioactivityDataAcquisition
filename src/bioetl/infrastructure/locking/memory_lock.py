"""A simple in-memory lock for local development and testing.
This lock is not distributed and only works within a single process.
"""

import asyncio
import time

from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID


class MemoryLock(LockPort):
    """A simple in-memory lock for local development and testing."""

    def __init__(self) -> None:
        """Initialize memory lock."""
        self._locks: dict[str, tuple[str, asyncio.Lock]] = {}
        self._global_lock = asyncio.Lock()

    async def _try_acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
    ) -> bool:
        """Attempt to acquire the lock once without waiting.

        Args:
            key: Lock key.
            owner_id: Owner identifier.
            ttl: Time-to-live (unused in memory lock).

        Returns:
            True if lock was acquired, False otherwise.

        """
        async with self._global_lock:
            if key in self._locks:
                _existing_owner, lock = self._locks[key]
                if lock.locked():
                    # Strictly non-reentrant: cannot acquire if already locked
                    return False

            # Create new lock or reuse existing unlocked one
            if key not in self._locks:
                lock = asyncio.Lock()
                self._locks[key] = (str(owner_id), lock)
            else:
                # Lock exists but is not locked - update owner and reuse
                _, lock = self._locks[key]
                self._locks[key] = (str(owner_id), lock)

            # Acquire the asyncio.Lock
            if not lock.locked():
                await lock.acquire()
                return True

            return str(owner_id) == self._locks[key][0]

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
            key: Lock key.
            owner_id: Owner identifier.
            ttl: Time-to-live (unused in memory lock).
            wait: If True, wait for lock to become available.
            wait_timeout: Maximum time to wait in seconds.
            exclusive: Exclusive lock flag (unused in memory lock).

        Returns:
            True if lock was acquired, False otherwise.

        """
        # Try to acquire immediately
        if await self._try_acquire(key, owner_id, ttl):
            return True

        # If not waiting, return immediately
        if not wait:
            return False

        # Wait for lock with timeout
        start = time.monotonic()
        while time.monotonic() - start < wait_timeout:
            if await self._try_acquire(key, owner_id, ttl):
                return True
            await asyncio.sleep(0.1)

        return False

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock."""
        async with self._global_lock:
            if key not in self._locks:
                return False

            existing_owner, lock = self._locks[key]
            if existing_owner != str(owner_id):
                return False

            if lock.locked():
                lock.release()

            del self._locks[key]
            return True

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Heartbeat a lock."""
        async with self._global_lock:
            if key not in self._locks:
                return False
            existing_owner, _lock = self._locks[key]
            return existing_owner == str(owner_id)

    async def aclose(self) -> None:
        """Close all locks."""
        async with self._global_lock:
            for _, (_, lock) in self._locks.items():
                if lock.locked():
                    lock.release()
            self._locks.clear()
