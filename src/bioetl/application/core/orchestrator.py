"""Pipeline Orchestrator.

Handles pipeline lifecycle, signals, and graceful shutdown.

Refactored per ADR-0005 to use ShutdownSignal for coordination.
"""

from __future__ import annotations

import asyncio
import signal
import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.config import get_settings
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


class PipelineOrchestrator:
    """Manages pipeline execution, lifecycle, and shutdown signals.

    The orchestrator coordinates:
    1. Lock acquisition and release
    2. Heartbeat maintenance
    3. Shutdown signal handling
    4. Metrics recording
    """

    def __init__(
        self,
        pipeline: "BasePipeline",
        *,
        shutdown_signal: ShutdownSignal | None = None,
    ) -> None:
        """Initialize orchestrator.

        Args:
            pipeline: The pipeline to orchestrate.
            shutdown_signal: Shared signal for shutdown coordination.
                           If None, creates a new signal (legacy mode).
        """
        self.pipeline = pipeline
        self.shutdown_signal = shutdown_signal or ShutdownSignal()
        self.heartbeat_task: asyncio.Task[None] | None = None

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown was requested (backward compatibility)."""
        return self.shutdown_signal.is_requested

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        start_time = time.time()
        status = "success"

        self.pipeline.logger.info(
            f"Starting pipeline: {self.pipeline.pipeline_name}",
            extra={"stage": "startup", "run_type": self.pipeline.run_type.value},
        )
        self._setup_shutdown_handlers()

        lock_key = f"{self.pipeline.provider}_{self.pipeline.entity_type}"
        exclusive = self.pipeline.run_type in (RunType.BACKFILL, RunType.REBUILD)

        try:
            acquired = await self.pipeline.lock.acquire(
                key=lock_key,
                owner_id=self.pipeline.run_id,
                wait=False,
                exclusive=exclusive,
            )
            if not acquired:
                self.pipeline.logger.error(f"Failed to acquire lock for {lock_key}")
                status = "lock_failed"
                return

            self.pipeline.logger.info(f"Lock acquired for {lock_key}")
            self.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(lock_key, exclusive)
            )

            watermark = await self.pipeline.checkpoint_manager.load_checkpoint()
            await self.pipeline.executor.execute(
                watermark=watermark, limit=self.pipeline.limit
            )
            await self.pipeline.checkpoint_manager.delete_checkpoint()

            self.pipeline.logger.info(
                "Pipeline completed successfully",
                extra={
                    "stage": "complete",
                    "records_fetched": self.pipeline.executor.records_fetched,
                },
            )
        except PipelineShutdownError:
            self.pipeline.logger.warning(
                "Pipeline shutdown requested", extra={"stage": "shutdown"}
            )
            status = "shutdown"
            raise
        except Exception as e:
            self.pipeline.logger.error(f"Pipeline failed: {e}", exc_info=True)
            status = "failure"
            raise
        finally:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            await self.pipeline.lock.release(
                lock_key, self.pipeline.run_id, exclusive=exclusive
            )
            self.pipeline.logger.info("Lock released", extra={"stage": "cleanup"})

            # Record metrics via port (if available)
            duration = time.time() - start_time
            if self.pipeline.metrics:
                await self.pipeline.metrics.observe_histogram(
                    "pipeline_duration_seconds",
                    duration,
                    {
                        "pipeline_name": self.pipeline.pipeline_name,
                        "run_type": self.pipeline.run_type.value,
                        "status": status,
                    },
                )

                for layer, count in [
                    ("bronze", self.pipeline.executor.records_bronze),
                    ("silver", self.pipeline.executor.records_silver),
                    ("gold", self.pipeline.executor.records_gold),
                ]:
                    await self.pipeline.metrics.increment_counter(
                        "records_processed_total",
                        count,
                        {
                            "pipeline_name": self.pipeline.pipeline_name,
                            "run_type": self.pipeline.run_type.value,
                            "layer": layer,
                        },
                    )

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        """Background task to maintain lock via heartbeat."""
        settings = get_settings()
        interval = settings.pipeline.heartbeat_interval

        while not self.shutdown_signal.is_requested:
            await asyncio.sleep(interval)
            success = await self.pipeline.lock.heartbeat(
                lock_key, self.pipeline.run_id, exclusive=exclusive
            )
            if not success:
                self.pipeline.logger.error("Lost lock during execution!")
                self.shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")

    def _setup_shutdown_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, _: Any) -> None:
            self.pipeline.logger.warning(
                f"Received signal {signum}, initiating graceful shutdown"
            )
            self.shutdown_signal.request()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)


# Re-export for backward compatibility
__all__ = ["PipelineOrchestrator", "PipelineShutdownError"]
