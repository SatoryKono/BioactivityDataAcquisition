"""Lock Manager for ETL Pipelines.

Refactored per ADR-0005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.config import get_settings
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    import structlog


class LockManager:
    """Manages acquiring, releasing, and maintaining distributed locks.

    This manager handles the full lifecycle of pipeline locks:
    1. Acquiring exclusive or shared locks
    2. Maintaining locks via heartbeat
    3. Releasing locks on completion or failure

    Can be used as an async context manager for automatic cleanup.
    """

    def __init__(
        self,
        lock_port: LockPort,
        run_id: RunID,
        lock_key: str,
        exclusive: bool,
        logger: "structlog.BoundLogger",
        shutdown_signal: ShutdownSignal,
    ) -> None:
        """Initialize LockManager with explicit dependencies.

        Args:
            lock_port: Port for distributed lock operations.
            run_id: Unique identifier for this pipeline run.
            lock_key: Key to use for the lock (e.g., "provider_entity").
            exclusive: Whether to acquire exclusive lock.
            logger: Logger for lock events.
            shutdown_signal: Shared signal for shutdown coordination.
        """
        self._lock = lock_port
        self._run_id = run_id
        self._lock_key = lock_key
        self._exclusive = exclusive
        self._logger = logger
        self._shutdown_signal = shutdown_signal
        self._heartbeat_task: asyncio.Task[None] | None = None

    @classmethod
    def create(
        cls,
        lock_port: LockPort,
        run_id: RunID,
        provider: str,
        entity_type: str,
        run_type: RunType,
        logger: "structlog.BoundLogger",
        shutdown_signal: ShutdownSignal,
    ) -> "LockManager":
        """Factory method for creating LockManager with common parameters.

        Args:
            lock_port: Port for distributed lock operations.
            run_id: Unique identifier for this pipeline run.
            provider: Data provider name (e.g., "chembl").
            entity_type: Entity type being processed.
            run_type: Type of pipeline run (determines exclusivity).
            logger: Logger for lock events.
            shutdown_signal: Shared signal for shutdown coordination.
        """
        lock_key = f"{provider}_{entity_type}"
        exclusive = run_type in (RunType.BACKFILL, RunType.REBUILD)

        return cls(
            lock_port=lock_port,
            run_id=run_id,
            lock_key=lock_key,
            exclusive=exclusive,
            logger=logger,
            shutdown_signal=shutdown_signal,
        )

    async def acquire(self) -> bool:
        """Acquire the lock.

        Returns:
            True if lock was acquired, False otherwise.
        """
        acquired = await self._lock.acquire(
            key=self._lock_key,
            owner_id=self._run_id,
            wait=False,
            exclusive=self._exclusive,
        )

        if acquired:
            self._logger.info(f"Lock acquired for {self._lock_key}")
        else:
            self._logger.error(f"Failed to acquire lock for {self._lock_key}")

        return acquired

    async def release(self) -> None:
        """Release the lock and stop heartbeat."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        await self._lock.release(
            self._lock_key, self._run_id, exclusive=self._exclusive
        )
        self._logger.info("Lock released", extra={"stage": "cleanup"})

    def start_heartbeat(self) -> None:
        """Start background heartbeat task."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Background task to maintain lock via heartbeat."""
        settings = get_settings()
        interval = settings.pipeline.heartbeat_interval

        while not self._shutdown_signal.is_requested:
            await asyncio.sleep(interval)
            success = await self._lock.heartbeat(
                self._lock_key, self._run_id, exclusive=self._exclusive
            )
            if not success:
                self._logger.error("Lost lock during execution!")
                self._shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")

    async def __aenter__(self) -> "LockManager":
        """Async context manager entry - acquire lock."""
        acquired = await self.acquire()
        if not acquired:
            raise PipelineShutdownError(f"Failed to acquire lock for {self._lock_key}")
        self.start_heartbeat()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit - release lock."""
        await self.release()
