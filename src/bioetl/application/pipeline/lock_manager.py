"""Lock manager for ETL pipelines.

Handles distributed lock acquisition, release, and heartbeat maintenance.
"""

import asyncio
from logging import Logger

from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID


class PipelineLockLostError(Exception):
    """Raised when pipeline loses its lock."""

    pass


class LockManager:
    """Manages distributed lock lifecycle for pipelines.

    Responsibilities:
    - Lock acquisition with exclusive/shared mode
    - Heartbeat maintenance during execution
    - Clean lock release on completion
    """

    def __init__(
        self,
        lock: LockPort,
        run_id: RunID,
        logger: Logger,
    ) -> None:
        self._lock = lock
        self._run_id = run_id
        self._logger = logger
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._shutdown_callback: callable | None = None

    async def acquire(self, key: str, exclusive: bool) -> bool:
        """Acquire lock for the given key.

        Args:
            key: Lock key (usually provider_entity)
            exclusive: True for exclusive lock (backfill/rebuild)

        Returns:
            True if lock acquired, False otherwise
        """
        acquired = await self._lock.acquire(
            key=key, owner_id=self._run_id, wait=False, exclusive=exclusive
        )
        if acquired:
            self._logger.info(f"Lock acquired for {key}")
        else:
            self._logger.error(f"Failed to acquire lock for {key}")
        return acquired

    async def release(self, key: str, exclusive: bool) -> None:
        """Release lock for the given key."""
        await self._lock.release(key, self._run_id, exclusive=exclusive)
        self._logger.info("Lock released", extra={"stage": "cleanup"})

    def start_heartbeat(
        self, key: str, exclusive: bool, shutdown_callback: callable
    ) -> None:
        """Start heartbeat loop for lock maintenance.

        Args:
            key: Lock key
            exclusive: Lock mode
            shutdown_callback: Called when lock is lost
        """
        self._shutdown_callback = shutdown_callback
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(key, exclusive)
        )

    def stop_heartbeat(self) -> None:
        """Stop heartbeat loop."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self, key: str, exclusive: bool) -> None:
        """Send periodic heartbeats to maintain lock."""
        while True:
            await asyncio.sleep(20)
            success = await self._lock.heartbeat(key, self._run_id, exclusive=exclusive)
            if not success:
                self._logger.error("Lost lock during execution!")
                if self._shutdown_callback:
                    self._shutdown_callback()
                raise PipelineLockLostError("Lock lost")
