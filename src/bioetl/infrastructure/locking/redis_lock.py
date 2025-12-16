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

if TYPE_CHECKING:
    from uuid import UUID

    from redis.asyncio import Redis

    from bioetl.domain.types import RunID


class LockAcquisitionError(Exception):
    """Raised when lock cannot be acquired."""

    def __init__(self, key: str, current_owner: str | None = None) -> None:
        self.key = key
        self.current_owner = current_owner
        msg = f"Failed to acquire lock: {key}"
        if current_owner:
            msg += f" (owned by {current_owner})"
        super().__init__(msg)


class LockLostError(Exception):
    """Raised when lock is lost during execution.

    This is a CRITICAL error - worker MUST terminate before any commit.
    """

    def __init__(self, key: str, owner_id: str) -> None:
        self.key = key
        self.owner_id = owner_id
        super().__init__(
            f"Lock lost for key '{key}' by owner '{owner_id}'. "
            "CRITICAL: Terminate immediately, do not commit!"
        )


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

    async def acquire(
        self,
        key: str,
        owner_id: RunID | UUID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """Acquire distributed lock.

        Args:
            key: Lock key (e.g., 'chembl_activity')
            owner_id: Run ID of lock owner (fencing token)
            ttl: Time-to-live in seconds (default: default_ttl)
            wait: Wait for lock if unavailable
            wait_timeout: Maximum wait time in seconds (default: 300)
            exclusive: Acquire exclusive lock for backfill/rebuild

        Returns:
            True if lock acquired, False otherwise

        Raises:
            LockAcquisitionError: If wait=True and timeout exceeded
        """
        redis_key = self._make_key(key, exclusive)
        owner_str = self._owner_to_str(owner_id)
        ttl = ttl or self.default_ttl

        # If exclusive, check for regular lock
        if exclusive:
            regular_key = self._make_key(key)
            if await self.redis_client.exists(regular_key):
                return False
        else:
            # If regular, check for exclusive lock
            exclusive_key = self._make_key(key, exclusive=True)
            if await self.redis_client.exists(exclusive_key):
                return False

        # Try to acquire lock with SETNX + EXPIRE
        acquired = await self.redis_client.set(
            redis_key,
            owner_str,
            nx=True,  # Only set if not exists
            ex=ttl,  # Set expiration
        )

        if acquired:
            return True

        if not wait:
            return False

        # Wait mode: poll until lock is available or timeout
        elapsed = 0.0
        poll_interval = 0.5  # 500ms polling

        while elapsed < wait_timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            if exclusive:
                regular_key = self._make_key(key)
                if await self.redis_client.exists(regular_key):
                    continue
            else:
                exclusive_key = self._make_key(key, exclusive=True)
                if await self.redis_client.exists(exclusive_key):
                    continue

            acquired = await self.redis_client.set(
                redis_key,
                owner_str,
                nx=True,
                ex=ttl,
            )

            if acquired:
                return True

        # Timeout exceeded
        current_owner = await self.get_owner(key, exclusive)
        raise LockAcquisitionError(key, current_owner)

    async def release(
        self, key: str, owner_id: RunID | UUID, exclusive: bool = False
    ) -> bool:
        """Release lock (only if owner matches).

        Args:
            key: Lock key
            owner_id: Run ID of lock owner (must match)
            exclusive: Whether this was an exclusive lock

        Returns:
            True if released, False if not owned
        """
        await self._ensure_scripts()
        redis_key = self._make_key(key, exclusive)
        owner_str = self._owner_to_str(owner_id)

        result = await self.redis_client.evalsha(
            self._release_script,  # type: ignore[arg-type]
            1,  # Number of keys
            redis_key,
            owner_str,
        )

        if exclusive and bool(result):
            # Also release the regular lock
            regular_key = self._make_key(key)
            await self.redis_client.delete(regular_key)

        return bool(result)

    async def heartbeat(
        self, key: str, owner_id: RunID | UUID, exclusive: bool = False
    ) -> bool:
        """Refresh lock TTL (keep-alive).

        Args:
            key: Lock key
            owner_id: Run ID of lock owner (must match)
            exclusive: Whether this is an exclusive lock

        Returns:
            True if heartbeat successful, False if lock lost

        CRITICAL: If this returns False, worker MUST terminate immediately
        before attempting any writes!
        """
        await self._ensure_scripts()
        redis_key = self._make_key(key, exclusive)
        owner_str = self._owner_to_str(owner_id)

        result = await self.redis_client.evalsha(
            self._heartbeat_script,  # type: ignore[arg-type]
            1,  # Number of keys
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
        """Run continuous heartbeat loop.

        This coroutine should be run as a background task.
        It will raise LockLostError if the lock is lost.

        Args:
            key: Lock key
            owner_id: Run ID of lock owner
            on_lost: Optional event to set when lock is lost
            exclusive: Whether this is an exclusive lock

        Raises:
            LockLostError: If lock is lost during execution
        """
        total_duration = 0

        while True:
            await asyncio.sleep(self.heartbeat_interval)
            total_duration += self.heartbeat_interval

            # Check max duration
            if total_duration >= self.max_duration:
                # Force release after max duration
                await self.release(key, owner_id, exclusive)
                if on_lost:
                    on_lost.set()
                raise LockLostError(key, self._owner_to_str(owner_id))

            success = await self.heartbeat(key, owner_id, exclusive)
            if not success:
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
        if owner is None:
            return None
        if isinstance(owner, bytes):
            return owner.decode("utf-8")
        return str(owner)
