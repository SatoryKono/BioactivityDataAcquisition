"""Phase handlers for PipelineRunner decomposition.

Implements the Command pattern for pipeline phases, allowing individual
execution steps to be encapsulated and potentially executed independently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.postrun_service import PostrunService
    from bioetl.application.core.preflight_service import PreflightService
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import TracingPort


class PreflightHandler:
    """Handles infrastructure validation phase."""

    def __init__(self, service: PreflightService, services: PipelineServices) -> None:
        self._service = service
        self._services = services

    async def handle(self) -> None:
        """Execute preflight checks."""
        await self._service.validate_infrastructure(self._services)


class InitializationHandler:
    """Handles Medallion Lifecycle preparation phase."""

    def __init__(
        self,
        lifecycle: MedallionLifecycleService,
        config: PipelineConfig,
        runtime: RuntimeConfig,
    ) -> None:
        self._lifecycle = lifecycle
        self._config = config
        self._runtime = runtime

    async def handle(self) -> None:
        """Prepare medallion layers for run."""
        await self._lifecycle.prepare_for_run(
            config=self._config,
            runtime=self._runtime,
        )


class ExecutionHandler:
    """Handles main pipeline execution phase."""

    def __init__(
        self,
        executor: BatchExecutor,
        checkpoint_manager: CheckpointManager,
        runtime: RuntimeConfig,
    ) -> None:
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager
        self._runtime = runtime

    async def handle(self) -> None:
        """Execute pipeline batch processing."""
        await self._checkpoint_manager.load_checkpoint()
        await self._executor.execute(
            limit=self._runtime.limit,
            query=self._runtime.query,
        )


class PostrunHandler:
    """Handles post-run tasks (DQ, Vacuum, Cleanup)."""

    def __init__(
        self,
        service: PostrunService,
        executor: BatchExecutor,
        checkpoint_manager: CheckpointManager,
    ) -> None:
        self._service = service
        self._executor = executor
        self._checkpoint_manager = checkpoint_manager

    async def handle(self) -> None:
        """Execute post-run operations."""
        dq_context = self._executor.get_dq_context()
        await self._service.run(
            executor=self._executor,
            dq_context=dq_context,
        )
        await self._checkpoint_manager.delete_checkpoint()


class CleanupHandler:
    """Handles final resource cleanup."""

    def __init__(
        self,
        service: PostrunService,
        tracer: TracingPort | None,
    ) -> None:
        self._service = service
        self._tracer = tracer

    async def handle(self) -> None:
        """Execute cleanup operations."""
        await self._service.cleanup(self._tracer)
