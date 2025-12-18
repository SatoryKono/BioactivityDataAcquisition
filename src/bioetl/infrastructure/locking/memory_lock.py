"""
A simple in-memory lock for local development and testing.
This lock is not distributed and only works within a single process.
"""
import asyncio
from typing import Optional, Union, NewType

from bioetl.domain.ports import LockPort

# Define Key and Owner as simple strings for this context
Key = NewType("Key", str)
Owner = NewType("Owner", str)


class MemoryLock(LockPort):
    """A simple in-memory lock for local development and testing."""

    def __init__(self):
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        key: Key,
        owner_id: Owner,
        ttl: int | None = None,
        wait: bool = True,
        wait_timeout: Optional[Union[int, float]] = None,
        exclusive: bool = True,
    ) -> bool:
        try:
            if not wait:
                if self._lock.locked():
                    return False
                await self._lock.acquire()
                return True

            await asyncio.wait_for(self._lock.acquire(), timeout=wait_timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def release(self, key: Key, owner_id: Owner, exclusive: bool = True) -> bool:
        try:
            self._lock.release()
            return True
        except RuntimeError:  # release unlocked lock
            return False

    async def heartbeat(self, key: Key, owner_id: Owner, exclusive: bool = True) -> bool:
        # No-op for memory lock, always succeeds
        return True
