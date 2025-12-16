"""Lock Manager for ETL Pipelines."""

import asyncio
from typing import TYPE_CHECKING

from bioetl.application.core.orchestrator import PipelineShutdownError
from bioetl.config import get_settings
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


class LockManager:
    """Manages acquiring, releasing, and maintaining locks."""

    def __init__(self, pipeline: "BasePipeline"):
        self.pipeline = pipeline

    async def __aenter__(self) -> None:
        lock_key = f"{self.pipeline.provider}_{self.pipeline.entity_type}"
        exclusive = self.pipeline.run_type in (RunType.BACKFILL, RunType.REBUILD)

        acquired = await self.pipeline.lock.acquire(
            key=lock_key, owner_id=self.pipeline.run_id, wait=False, exclusive=exclusive
        )
        if not acquired:
            self.pipeline.logger.error(f"Failed to acquire lock for {lock_key}")
            raise PipelineShutdownError(f"Failed to acquire lock for {lock_key}")

        self.pipeline.logger.info(f"Lock acquired for {lock_key}")
        self.pipeline.orchestrator.heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(lock_key, exclusive)
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.pipeline.orchestrator.heartbeat_task:
            self.pipeline.orchestrator.heartbeat_task.cancel()

        lock_key = f"{self.pipeline.provider}_{self.pipeline.entity_type}"
        exclusive = self.pipeline.run_type in (RunType.BACKFILL, RunType.REBUILD)
        await self.pipeline.lock.release(
            lock_key, self.pipeline.run_id, exclusive=exclusive
        )
        self.pipeline.logger.info("Lock released", extra={"stage": "cleanup"})

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        settings = get_settings()
        interval = settings.pipeline.heartbeat_interval
        while not self.pipeline.orchestrator.shutdown_requested:
            await asyncio.sleep(interval)
            success = await self.pipeline.lock.heartbeat(
                lock_key, self.pipeline.run_id, exclusive=exclusive
            )
            if not success:
                self.pipeline.logger.error("Lost lock during execution!")
                self.pipeline.orchestrator.shutdown_requested = True
                raise PipelineShutdownError("Lock lost")
