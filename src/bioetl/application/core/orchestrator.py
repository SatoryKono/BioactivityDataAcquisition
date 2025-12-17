"""Pipeline Orchestrator.

Handles pipeline lifecycle, signals, and graceful shutdown.

Refactored per ADR-0005:
- No self-reference to pipeline
- Uses explicit dependencies via from_components()
"""

from __future__ import annotations

import asyncio
import signal
import time
from typing import TYPE_CHECKING, Any

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.pipeline_config import (
    PipelineConfig,
    PipelineRuntimeConfig,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.executor import PipelineExecutor


class PipelineOrchestrator:
    """Manages pipeline execution, lifecycle, and shutdown signals.

    The orchestrator coordinates:
    1. Lock acquisition and release
    2. Heartbeat maintenance
    3. Shutdown signal handling
    4. Metrics recording

    No self-reference to pipeline - uses explicit dependencies.
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
        heartbeat_interval: int,
    ) -> None:
        """Initialize orchestrator with explicit dependencies.

        Args:
            config: Static pipeline configuration.
            runtime: Runtime execution parameters.
            services: I/O port dependencies.
            context: Pipeline execution context.
            executor: Pipeline executor.
            checkpoint_manager: Checkpoint manager.
            shutdown_signal: Shared shutdown signal.
            logger: Bound logger.
            heartbeat_interval: Interval for lock heartbeat.
        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._context = context
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self.shutdown_signal = shutdown_signal
        self._logger = logger
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task: asyncio.Task[None] | None = None

    @classmethod
    def from_components(
        cls,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
        context: PipelineContext,
        executor: "PipelineExecutor",
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        logger: "structlog.BoundLogger",
        heartbeat_interval: int,
    ) -> "PipelineOrchestrator":
        """Create orchestrator from explicit components (new API).

        This factory method creates an orchestrator without circular dependencies.
        """
        return cls(
            config=config,
            runtime=runtime,
            services=services,
            context=context,
            executor=executor,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=logger,
            heartbeat_interval=heartbeat_interval,
        )

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown was requested (backward compatibility)."""
        return self.shutdown_signal.is_requested

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        start_time = time.time()
        status = "success"

        self._logger.info(
            f"Starting pipeline: {self._config.pipeline_name}",
            extra={"stage": "startup", "run_type": self._runtime.run_type.value},
        )
        self._setup_shutdown_handlers()

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
            await self._executor.execute(watermark=watermark, limit=self._runtime.limit)
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

            # Record metrics via port (sync methods, no await needed)
            duration = time.time() - start_time
            self._services.metrics.observe_histogram(
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
                self._services.metrics.increment_counter(
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
        while not self.shutdown_signal.is_requested:
            await asyncio.sleep(self.heartbeat_interval)
            success = await self._services.lock.heartbeat(
                lock_key, self._context.run_id, exclusive=exclusive
            )
            if not success:
                self._logger.error("Lost lock during execution!")
                self.shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")

    def _setup_shutdown_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, _: Any) -> None:
            self._logger.warning(
                f"Received signal {signum}, initiating graceful shutdown"
            )
            self.shutdown_signal.request()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)


# Re-export for backward compatibility
__all__ = ["PipelineOrchestrator", "PipelineShutdownError"]
