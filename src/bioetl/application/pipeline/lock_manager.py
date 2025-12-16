"""Lock management for ETL pipelines."""

import asyncio
import contextlib
import signal
from typing import TYPE_CHECKING, Any

from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.infrastructure.observability.logging import PipelineLogger


class PipelineLockManager:
    """Manages distributed locks for pipeline execution.

    Handles:
    - Lock acquisition with exclusive/shared modes
    - Heartbeat loop to maintain lock
    - Graceful release on shutdown
    """

    def __init__(
        self,
        lock: LockPort,
        run_id: RunID,
        logger: "PipelineLogger",
    ) -> None:
        self.lock = lock
        self.run_id = run_id
        self.logger = logger
        self.heartbeat_task: asyncio.Task[None] | None = None
        self._shutdown_requested = False

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    @shutdown_requested.setter
    def shutdown_requested(self, value: bool) -> None:
        self._shutdown_requested = value

    async def acquire(self, lock_key: str, exclusive: bool) -> bool:
        """Acquire lock and start heartbeat."""
        acquired = await self.lock.acquire(
            key=lock_key, owner_id=self.run_id, wait=False, exclusive=exclusive
        )
        if not acquired:
            self.logger.error(f"Failed to acquire lock for {lock_key}")
            return False

        self.logger.info(f"Lock acquired for {lock_key}")
        self.heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(lock_key, exclusive)
        )
        return True

    async def release(self, lock_key: str, exclusive: bool) -> None:
        """Stop heartbeat and release lock."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.heartbeat_task
        await self.lock.release(lock_key, self.run_id, exclusive=exclusive)
        self.logger.info("Lock released", extra={"stage": "cleanup"})

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        """Maintain lock with periodic heartbeats."""
        while not self._shutdown_requested:
            await asyncio.sleep(20)
            success = await self.lock.heartbeat(
                lock_key, self.run_id, exclusive=exclusive
            )
            if not success:
                self.logger.error("Lost lock during execution!")
                self._shutdown_requested = True
                from bioetl.application.pipeline.base import PipelineShutdownError

                raise PipelineShutdownError("Lock lost")

    def setup_shutdown_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def handler(signum: int, _: Any) -> None:
            self.logger.warning(f"Signal {signum}, initiating shutdown")
            self._shutdown_requested = True

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
