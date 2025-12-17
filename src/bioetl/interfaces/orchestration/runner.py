"""Pipeline Runner.

This is a "Driving Adapter" in the Hexagonal Architecture.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_config import (
    PipelineConfig,
    PipelineRuntimeConfig,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.infrastructure.config import get_settings
from bioetl.domain.context import PipelineContext

if TYPE_CHECKING:
    import structlog
    from bioetl.application.core.executor import PipelineExecutor


class PipelineRunner:
    """
    Manages the execution lifecycle of a pipeline.
    It coordinates application services like locking and checkpointing,
    but remains decoupled from the core business logic of the pipeline itself.
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

        # The runner is responsible for creating application services
        settings = get_settings()
        self._lock_manager = LockManager.create(
            lock_port=self._services.lock,
            run_id=self._context.run_id,
            provider=self._config.provider,
            entity_type=self._config.entity_type,
            run_type=self._runtime.run_type,
            heartbeat_interval=settings.pipeline.heartbeat_interval,
            logger=self._logger,
            shutdown_signal=self.shutdown_signal,
        )

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        start_time = time.time()
        status = "success"

        self._logger.info(
            f"Starting pipeline: {self._config.pipeline_name}",
            extra={"stage": "startup", "run_type": self._runtime.run_type.value},
        )

        try:
            async with self._services, self._lock_manager:
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
            # Do not re-raise, allow finally block to run
        except Exception as e:
            self._logger.error(f"Pipeline failed: {e}", exc_info=True)
            status = "failure"
            raise  # Re-raise after logging
        finally:
            # Metrics recording (sync methods, no await needed)
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
            # ... other metrics ...
