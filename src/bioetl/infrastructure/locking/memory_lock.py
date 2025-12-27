"""A simple in-memory lock for local development and testing.

This lock is not distributed and only works within a single process.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID

# Default TTL check interval in seconds
_TTL_CHECK_INTERVAL = 1.0


class MemoryLock(LockPort):
    """A simple in-memory lock for local development and testing.

    Supports TTL-based automatic lock expiration via a background task.
    """

    def __init__(self, ttl_check_interval: float = _TTL_CHECK_INTERVAL) -> None:
        """Initialize memory lock.

        Args:
            ttl_check_interval: Interval in seconds between TTL checks.
        """
        # Lock data: key -> (owner_id, asyncio.Lock, expires_at, original_ttl)
        self._locks: dict[str, tuple[str, asyncio.Lock, float | None, int | None]] = {}
        self._global_lock = asyncio.Lock()
        self._ttl_check_interval = ttl_check_interval
        self._ttl_checker_task: asyncio.Task[None] | None = None
        self._closed = False

    async def _start_ttl_checker(self) -> None:
        """Start the TTL checker background task if not already running."""
        if self._ttl_checker_task is None or self._ttl_checker_task.done():
            self._ttl_checker_task = asyncio.create_task(self._ttl_checker_loop())

    async def _ttl_checker_loop(self) -> None:
        """Background task to check and release expired locks."""
        while not self._closed:
            await asyncio.sleep(self._ttl_check_interval)
            await self._release_expired_locks()

    async def _release_expired_locks(self) -> None:
        """Release all locks that have exceeded their TTL."""
        current_time = time.monotonic()
        async with self._global_lock:
            expired_keys = [
                key
                for key, (_, lock, expires_at, _) in self._locks.items()
                if expires_at is not None
                and current_time > expires_at
                and lock.locked()
            ]
            for key in expired_keys:
                _, lock, _, _ = self._locks[key]
                if lock.locked():
                    lock.release()
                del self._locks[key]

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
            ttl: Time-to-live in seconds. If None, lock does not expire.

        Returns:
            True if lock was acquired, False otherwise.

        """
        async with self._global_lock:
            if key in self._locks:
                _existing_owner, lock, _, _ = self._locks[key]
                if lock.locked():
                    # Strictly non-reentrant: cannot acquire if already locked
                    return False

            # Calculate expiration time
            expires_at: float | None = None
            if ttl is not None:
                expires_at = time.monotonic() + ttl

            # Create new lock or reuse existing unlocked one
            if key not in self._locks:
                lock = asyncio.Lock()
                self._locks[key] = (str(owner_id), lock, expires_at, ttl)
            else:
                # Lock exists but is not locked - update owner and reuse
                _, lock, _, _ = self._locks[key]
                self._locks[key] = (str(owner_id), lock, expires_at, ttl)

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
            ttl: Time-to-live in seconds. If set, lock expires after TTL.
            wait: If True, wait for lock to become available.
            wait_timeout: Maximum time to wait in seconds.
            exclusive: Exclusive lock flag (unused in memory lock).

        Returns:
            True if lock was acquired, False otherwise.

        """
        # Start TTL checker if acquiring with TTL
        if ttl is not None:
            await self._start_ttl_checker()

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

            existing_owner, lock, _, _ = self._locks[key]
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
        """Heartbeat a lock to extend its TTL.

        Args:
            key: Lock key.
            owner_id: Owner identifier.
            exclusive: Exclusive lock flag (unused in memory lock).

        Returns:
            True if heartbeat succeeded, False otherwise.
        """
        async with self._global_lock:
            if key not in self._locks:
                return False
            existing_owner, lock, _, original_ttl = self._locks[key]
            if existing_owner != str(owner_id):
                return False

            # Extend TTL using the original TTL value
            if original_ttl is not None:
                new_expires_at = time.monotonic() + original_ttl
                self._locks[key] = (existing_owner, lock, new_expires_at, original_ttl)

            return True

    async def validate_owner(
        self,
        key: str,
        owner_id: RunID,
    ) -> bool:
        """Validate that the given owner_id holds the lock.

        This is the Safety Guard: before writing to storage, the writer
        MUST validate that it still holds the lock.

        Args:
            key: Lock key.
            owner_id: Owner identifier to validate.

        Returns:
            True if owner_id currently holds the lock, False otherwise.
        """
        async with self._global_lock:
            if key not in self._locks:
                return False

            existing_owner, lock, expires_at, _ = self._locks[key]

            # Check if lock is still held
            if not lock.locked():
                return False

            # Check if lock has expired
            if expires_at is not None and time.monotonic() > expires_at:
                return False

            # Check owner matches
            return existing_owner == str(owner_id)

    async def aclose(self) -> None:
        """Close all locks and stop background tasks."""
        self._closed = True

        # Stop the TTL checker task
        if self._ttl_checker_task is not None:
            self._ttl_checker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ttl_checker_task
            self._ttl_checker_task = None

        async with self._global_lock:
            for _, (_, lock, _, _) in self._locks.items():
                if lock.locked():
                    lock.release()
            self._locks.clear()
