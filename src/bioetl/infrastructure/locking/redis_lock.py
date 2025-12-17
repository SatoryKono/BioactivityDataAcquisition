"""Redis-based distributed lock implementation.

Implements RULES.md Section 3.3 distributed locking requirements:
- Redis SETNX + EXPIRE (REQ-LOCK-001)
- TTL: 60 seconds (REQ-LOCK-002)
- Heartbeat: every 20 seconds (REQ-LOCK-003)
- Fencing token: owner_id (REQ-LOCK-005)
- Max duration: 4 hours

Safety invariant:
- Lost lock = lost write permission
- Heartbeat failure -> immediate shutdown before commit
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import LockAcquisitionError, LockLostError

if TYPE_CHECKING:
    from uuid import UUID

    from redis.asyncio import Redis

    from bioetl.domain.types import RunID

# Lua script for atomic release (only if owner matches)
RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script for atomic heartbeat (extend TTL only if owner matches)
HEARTBEAT_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


@dataclass
class RedisDistributedLock:
    """Redis-based distributed lock with heartbeat support.

    Implements LockPort interface from domain/ports.py.

    Args:
        redis_client: Async Redis client
        prefix: Key prefix for locks (default: "lock")
        default_ttl: Default TTL in seconds (default: 60)
        heartbeat_interval: Heartbeat interval in seconds (default: 20)
        max_duration: Maximum lock duration in seconds (default: 14400 = 4h)

    Example:
        >>> redis = Redis.from_url("redis://localhost:6379")
        >>> lock = RedisDistributedLock(redis_client=redis)
        >>> run_id = RunID(uuid4())
        >>> if await lock.acquire("chembl_activity", run_id):
        ...     try:
        ...         # Start heartbeat task
        ...         heartbeat_task = asyncio.create_task(
        ...             lock.heartbeat_loop("chembl_activity", run_id)
        ...         )
        ...         # Do work...
        ...     finally:
        ...         heartbeat_task.cancel()
        ...         await lock.release("chembl_activity", run_id)
    """

    redis_client: Redis
    prefix: str = "lock"
    default_ttl: int = 60
    heartbeat_interval: int = 20
    max_duration: int = 14400  # 4 hours

    _release_script: bytes | None = field(init=False, default=None)
    _heartbeat_script: bytes | None = field(init=False, default=None)

    async def _ensure_scripts(self) -> None:
        """Register Lua scripts with Redis."""
        if self._release_script is None:
            self._release_script = await self.redis_client.script_load(RELEASE_SCRIPT)
        if self._heartbeat_script is None:
            self._heartbeat_script = await self.redis_client.script_load(
                HEARTBEAT_SCRIPT
            )

    def _make_key(self, key: str, exclusive: bool = False) -> str:
        """Create full Redis key with prefix."""
        if exclusive:
            return f"{self.prefix}:{key}:exclusive"
        return f"{self.prefix}:{key}"

    def _owner_to_str(self, owner_id: RunID | UUID) -> str:
        """Convert owner ID to string."""
        return str(owner_id)

    async def _try_acquire(
        self, key: str, owner_id: str, ttl: int, exclusive: bool
    ) -> bool:
        """Attempt to acquire the lock once."""
        redis_key = self._make_key(key, exclusive)
        if exclusive:
            regular_key = self._make_key(key)
            if await self.redis_client.exists(regular_key):
                return False
        else:
            exclusive_key = self._make_key(key, exclusive=True)
            if await self.redis_client.exists(exclusive_key):
                return False

        return await self.redis_client.set(redis_key, owner_id, nx=True, ex=ttl)

    async def _wait_for_lock(
        self, key: str, owner_id: str, ttl: int, timeout: int, exclusive: bool
    ) -> bool:
        """Wait for the lock to become available."""
        elapsed = 0.0
        poll_interval = 0.5

        while elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            if await self._try_acquire(key, owner_id, ttl, exclusive):
                return True
        return False

    async def acquire(
        self,
        key: str,
        owner_id: RunID | UUID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """Acquire distributed lock."""
        owner_str = self._owner_to_str(owner_id)
        ttl = ttl or self.default_ttl

        if await self._try_acquire(key, owner_str, ttl, exclusive):
            return True

        if not wait:
            return False

        if await self._wait_for_lock(key, owner_str, ttl, wait_timeout, exclusive):
            return True

        current_owner = await self.get_owner(key, exclusive)
        raise LockAcquisitionError(key, current_owner)

    async def release(
        self, key: str, owner_id: RunID | UUID, exclusive: bool = False
    ) -> bool:
        """Release lock (only if owner matches)."""
        await self._ensure_scripts()
        redis_key = self._make_key(key, exclusive)
        owner_str = self._owner_to_str(owner_id)

        result = await self.redis_client.evalsha(
            self._release_script, 1, redis_key, owner_str
        )

        if exclusive and bool(result):
            regular_key = self._make_key(key)
            await self.redis_client.delete(regular_key)

        return bool(result)

    async def heartbeat(
        self, key: str, owner_id: RunID | UUID, exclusive: bool = False
    ) -> bool:
        """Refresh lock TTL (keep-alive)."""
        await self._ensure_scripts()
        redis_key = self._make_key(key, exclusive)
        owner_str = self._owner_to_str(owner_id)

        result = await self.redis_client.evalsha(
            self._heartbeat_script,
            1,
            redis_key,
            owner_str,
            str(self.default_ttl),
        )
        return bool(result)

    async def heartbeat_loop(
        self,
        key: str,
        owner_id: RunID | UUID,
        on_lost: asyncio.Event | None = None,
        exclusive: bool = False,
    ) -> None:
        """Run continuous heartbeat loop."""
        total_duration = 0

        while True:
            await asyncio.sleep(self.heartbeat_interval)
            total_duration += self.heartbeat_interval

            if total_duration >= self.max_duration:
                await self.release(key, owner_id, exclusive)
                if on_lost:
                    on_lost.set()
                raise LockLostError(key, self._owner_to_str(owner_id))

            if not await self.heartbeat(key, owner_id, exclusive):
                if on_lost:
                    on_lost.set()
                raise LockLostError(key, self._owner_to_str(owner_id))

    async def is_locked(self, key: str, exclusive: bool = False) -> bool:
        """Check if lock exists."""
        redis_key = self._make_key(key, exclusive)
        return await self.redis_client.exists(redis_key) > 0

    async def get_owner(self, key: str, exclusive: bool = False) -> str | None:
        """Get current lock owner ID."""
        redis_key = self._make_key(key, exclusive)
        owner = await self.redis_client.get(redis_key)
        if isinstance(owner, bytes):
            return owner.decode("utf-8")
        return owner

    async def aclose(self) -> None:
        """Close the Redis connection.

        Implements the aclose() method required by LockPort protocol.
        """
        if hasattr(self.redis_client, "aclose"):
            await self.redis_client.aclose()
        elif hasattr(self.redis_client, "close"):
            await self.redis_client.close()
