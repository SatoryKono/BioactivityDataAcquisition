"""A simple in-memory lock for local development and testing.

This lock is process-local and only coordinates tasks within one process.
"""

from __future__ import annotations

from typing import override

__all__ = ["MemoryLock"]


import asyncio
import contextlib
import time

from bioetl.domain.locking import FencingToken
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID

# Default TTL check interval in seconds
_TTL_CHECK_INTERVAL = 1.0

# Lock data: owner_id, asyncio.Lock, expires_at, original_ttl, sequence
type _LockEntry = tuple[str, asyncio.Lock, float | None, int | None, int | None]


def _renew_soft_expired_entry(
    entry: _LockEntry,
    *,
    now: float,
) -> _LockEntry:
    """Renew a still-held entry when soft TTL has elapsed."""
    owner, lock, expires_at, original_ttl, sequence = entry
    if expires_at is None or now <= expires_at or original_ttl is None:
        return entry
    return (owner, lock, now + original_ttl, original_ttl, sequence)


class MemoryLock(LockPort):
    """Process-local lock with optional TTL and fencing tokens."""

    def __init__(self, ttl_check_interval: float = _TTL_CHECK_INTERVAL) -> None:
        """Initialize memory lock.

        Args:
            ttl_check_interval: Interval in seconds between TTL checks.
        """
        self._locks: dict[str, _LockEntry] = {}
        self._global_lock = asyncio.Lock()
        self._ttl_check_interval = ttl_check_interval
        self._ttl_checker_task: asyncio.Task[None] | None = None
        self._closed = False
        self._sequence: int = 0

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
        """Drop soft-expired lock entries that are no longer held.

        Process-local MemoryLock must not force-release a still-held
        ``asyncio.Lock``. Long write stages can delay heartbeats while the
        owner coroutine is still actively writing; forcibly dropping the
        entry mid-write surfaces as ``LockNotHeldError`` on the next layer.
        Abandoned held locks are freed only by explicit ``release()`` or
        process exit (same lifetime as the in-memory map).
        """
        current_time = time.monotonic()
        async with self._global_lock:
            expired_keys = [
                key
                for key, (_, lock, expires_at, _, _) in self._locks.items()
                if expires_at is not None
                and current_time > expires_at
                and not lock.locked()
            ]
            for key in expired_keys:
                del self._locks[key]

    async def _try_acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
    ) -> FencingToken | None:
        """Attempt to acquire the lock once without waiting."""
        async with self._global_lock:
            if key in self._locks:
                _existing_owner, lock, _, _, _ = self._locks[key]
                if lock.locked():
                    # Strictly non-reentrant: cannot acquire if already locked
                    return None
            else:
                lock = asyncio.Lock()

            expires_at = time.monotonic() + ttl if ttl is not None else None
            if not lock.locked():
                await lock.acquire()
                self._sequence += 1
                sequence = self._sequence
                self._locks[key] = (str(owner_id), lock, expires_at, ttl, sequence)
                return FencingToken(
                    sequence=sequence,
                    key=key,
                    owner_id=owner_id,
                    issued_at=time.monotonic(),
                )
            return None

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> FencingToken | None:
        """Acquire a lock, optionally waiting until available."""
        del exclusive  # unused for process-local memory locks
        if ttl is not None:
            await self._start_ttl_checker()

        token = await self._try_acquire(key, owner_id, ttl)
        if token is not None or not wait:
            return token

        start = time.monotonic()
        while time.monotonic() - start < wait_timeout:
            token = await self._try_acquire(key, owner_id, ttl)
            if token is not None:
                return token
            await asyncio.sleep(0.1)
        return None

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock held by the specified owner."""
        del exclusive
        async with self._global_lock:
            if key not in self._locks:
                return False
            existing_owner, lock, _, _, _ = self._locks[key]
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
        """Heartbeat a lock to extend its TTL."""
        del exclusive
        async with self._global_lock:
            if key not in self._locks:
                return False
            existing_owner, lock, _, original_ttl, sequence = self._locks[key]
            if existing_owner != str(owner_id):
                return False
            if original_ttl is not None:
                self._locks[key] = (
                    existing_owner,
                    lock,
                    time.monotonic() + original_ttl,
                    original_ttl,
                    sequence,
                )
            return True

    async def validate_owner(self, key: str, owner_id: RunID) -> bool:
        """Validate that the given owner_id still holds the lock."""
        async with self._global_lock:
            entry = self._locks.get(key)
            if entry is None:
                return False
            existing_owner, lock, _, _, _ = entry
            if not lock.locked() or existing_owner != str(owner_id):
                return False
            # Soft-expired held ownership renews on validate so write stages
            # survive delayed heartbeats without dropping the lease.
            self._locks[key] = _renew_soft_expired_entry(entry, now=time.monotonic())
            return True

    async def validate_fencing_token(self, key: str, token: FencingToken) -> bool:
        """Validate that the given fencing token is still valid for the lock."""
        async with self._global_lock:
            entry = self._locks.get(key)
            if entry is None or token.key != key:
                return False
            existing_owner, lock, _, _, sequence = entry
            if (
                not lock.locked()
                or existing_owner != str(token.owner_id)
                or sequence is None
                or token.sequence != sequence
            ):
                return False
            self._locks[key] = _renew_soft_expired_entry(entry, now=time.monotonic())
            return True

    async def aclose(self) -> None:
        """Close all locks and stop background tasks."""
        self._closed = True
        if self._ttl_checker_task is not None:
            self._ttl_checker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ttl_checker_task
            self._ttl_checker_task = None

        async with self._global_lock:
            for _, lock, _, _, _ in self._locks.values():
                if lock.locked():
                    lock.release()
            self._locks.clear()
