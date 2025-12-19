"""
A simple in-memory lock for local development and testing.
This lock is not distributed and only works within a single process.
"""
import asyncio

from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID


class MemoryLock(LockPort):
    """A simple in-memory lock for local development and testing."""

    def __init__(self) -> None:
        self._locks: dict[str, tuple[str, asyncio.Lock]] = {}
        self._global_lock = asyncio.Lock()

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """Acquire a lock."""
        async with self._global_lock:
            # Check if key exists
            if key in self._locks:
                existing_owner, lock = self._locks[key]
                if lock.locked():
                    if existing_owner == str(owner_id):
                        return True  # Already owned

                    # If not waiting, fail immediately
                    if not wait:
                        return False

                    # If waiting, we need to release global lock to allow others to release
                    # But implementing per-key wait with global lock release is complex.
                    # For simple in-memory testing, we can just fail or sleep loop.
                    # Simplified: only support wait=False for now or assume test won't block.
                    # Real implementation of wait in memory lock requires Condition or similar.
                    # Given constraints, we will just fail if locked by other.
                    # TODO: Implement proper wait mechanism if needed for tests.
                    return False
            else:
                # Create new lock
                lock = asyncio.Lock()
                self._locks[key] = (str(owner_id), lock)

        # Acquire the specific lock
        # Note: We are already holding it logically by putting it in _locks map above
        # But to use asyncio.Lock semantics we acquire it.
        # However, since we are single process, the _locks map entry acts as the "held" state.
        # We simplify by just using the map presence as locked state.
        # But to support `lock.locked()`, we should actually acquire it.

        # Re-fetch lock to be sure
        _, lock = self._locks[key]
        if not lock.locked():
            await lock.acquire()
            return True

        return str(owner_id) == self._locks[key][0]

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
            existing_owner, lock = self._locks[key]
            return existing_owner == str(owner_id)

    async def aclose(self) -> None:
        """Close all locks."""
        async with self._global_lock:
            for _, (_, lock) in self._locks.items():
                if lock.locked():
                    lock.release()
            self._locks.clear()
