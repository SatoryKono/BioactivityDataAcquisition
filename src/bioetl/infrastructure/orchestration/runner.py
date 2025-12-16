"""Pipeline Runner.

Handles pipeline lifecycle, and graceful shutdown.
This is a "Driving Adapter" in the Hexagonal Architecture.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.config import get_settings
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    import structlog
    from bioetl.application.core.executor import PipelineExecutor


class PipelineRunner:
    """Manages pipeline execution, lifecycle, and shutdown signals.

    The runner coordinates:
    1. Lock acquisition and release
    2. Heartbeat maintenance
    3. Awaits shutdown signals (but doesn't listen for them)
    4. Metrics recording
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        context: PipelineContext,
        executor: "PipelineExecutor",
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        logger: "structlog.BoundLogger",
    ) -> None:
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self.shutdown_signal = shutdown_signal
        self._logger = logger
        self.heartbeat_task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        start_time = time.time()
        status = "success"

        self._logger.info(
            f"Starting pipeline: {self._config.pipeline_name}",
            extra={"stage": "startup", "run_type": self._runtime.run_type.value},
        )

        lock_key = f"{self._config.provider}_{self._config.entity_type}"
        exclusive = self._runtime.run_type in (RunType.BACKFILL, RunType.REBUILD)

        try:
            acquired = await self._services.lock.acquire(
                key=lock_key,
                owner_id=self._context.run_id,
                wait=False,
                exclusive=exclusive,
            )
            if not acquired:
                self._logger.error(f"Failed to acquire lock for {lock_key}")
                status = "lock_failed"
                return

            self._logger.info(f"Lock acquired for {lock_key}")
            self.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(lock_key, exclusive)
            )

            watermark = await self._checkpoint_manager.load_checkpoint()
            await self._executor.execute(
                watermark=watermark, limit=self._runtime.limit
            )
            await self._checkpoint_manager.delete_checkpoint()

            self._logger.info(
                "Pipeline completed successfully",
                extra={
                    "stage": "complete",
                    "records_fetched": self._executor.records_fetched,
                },
            )
        except PipelineShutdownError:
            self._logger.warning(
                "Pipeline shutdown requested", extra={"stage": "shutdown"}
            )
            status = "shutdown"
            raise
        except Exception as e:
            self._logger.error(f"Pipeline failed: {e}", exc_info=True)
            status = "failure"
            raise
        finally:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            await self._services.lock.release(
                lock_key, self._context.run_id, exclusive=exclusive
            )
            self._logger.info("Lock released", extra={"stage": "cleanup"})

            duration = time.time() - start_time
            await self._services.metrics.observe_histogram(
                "pipeline_duration_seconds",
                duration,
                {
                    "pipeline_name": self._config.pipeline_name,
                    "run_type": self._runtime.run_type.value,
                    "status": status,
                },
            )

            for layer, count in [
                ("bronze", self._executor.records_bronze),
                ("silver", self._executor.records_silver),
                ("gold", self._executor.records_gold),
            ]:
                await self._services.metrics.increment_counter(
                    "records_processed_total",
                    count,
                    {
                        "pipeline_name": self._config.pipeline_name,
                        "run_type": self._runtime.run_type.value,
                        "layer": layer,
                    },
                )

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        """Background task to maintain lock via heartbeat."""
        settings = get_settings()
        interval = settings.pipeline.heartbeat_interval

        while not self.shutdown_signal.is_requested:
            await asyncio.sleep(interval)
            success = await self._services.lock.heartbeat(
                lock_key, self._context.run_id, exclusive=exclusive
            )
            if not success:
                self._logger.error("Lost lock during execution!")
                self.shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")
