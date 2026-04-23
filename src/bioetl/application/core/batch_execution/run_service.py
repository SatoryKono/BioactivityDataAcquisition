"""Run/failure policy orchestration for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExecutionRunService"]


from collections.abc import Awaitable
from typing import Protocol

from bioetl.application.core.batch_execution._contracts import (
    BatchExecutionCountersSnapshot,
    BatchExecutionMemoryState,
)
from bioetl.application.core.batch_execution.lifecycle import (
    BatchExecutionContext,
    BatchExecutionLifecycleContext,
    BatchExecutionLifecycleService,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError


class _BatchExtractionLoopRunner(Protocol):
    """Callable that executes the extraction loop for one run."""

    def __call__(
        self,
        execution_context: BatchExecutionContext,
    ) -> Awaitable[None]: ...


class BatchExecutionRunService:
    """Coordinates one executor run across start, loop, and finalize paths."""

    def __init__(
        self,
        *,
        execution_lifecycle_service: BatchExecutionLifecycleService,
    ) -> None:
        """Initialize execution run service."""
        self._execution_lifecycle = execution_lifecycle_service

    async def execute(
        self,
        *,
        execution_context: BatchExecutionContext,
        run_loop: _BatchExtractionLoopRunner,
        execution_state: BatchExecutionCountersSnapshot,
        memory_state: BatchExecutionMemoryState,
    ) -> None:
        """Run the extraction loop and apply the correct finalization policy."""
        lifecycle_context = await self._execution_lifecycle.start_execution(
            execution_context
        )
        await self._run_with_finalization_policy(
            lifecycle_context=lifecycle_context,
            execution_context=execution_context,
            run_loop=run_loop,
            execution_state=execution_state,
            memory_state=memory_state,
        )

    async def _run_with_finalization_policy(
        self,
        *,
        lifecycle_context: BatchExecutionLifecycleContext,
        execution_context: BatchExecutionContext,
        run_loop: _BatchExtractionLoopRunner,
        execution_state: BatchExecutionCountersSnapshot,
        memory_state: BatchExecutionMemoryState,
    ) -> None:
        """Finalize success, shutdown, and runtime failure using one policy."""
        try:
            await run_loop(execution_context)
        except PipelineShutdownError:
            await self._execution_lifecycle.finalize_execution(
                execution_state,
                lifecycle_context,
                batch_size_reductions=memory_state.batch_size_reductions,
                min_batch_size_used=memory_state.min_batch_size_used,
                memory_decision_trace=memory_state.decision_trace_dicts(),
                shutdown=True,
            )
            raise
        except PIPELINE_EXECUTION_ERRORS as error:
            await self._execution_lifecycle.finalize_execution(
                execution_state,
                lifecycle_context,
                batch_size_reductions=memory_state.batch_size_reductions,
                min_batch_size_used=memory_state.min_batch_size_used,
                memory_decision_trace=memory_state.decision_trace_dicts(),
                error=error,
            )
            raise
        else:
            await self._execution_lifecycle.finalize_execution(
                execution_state,
                lifecycle_context,
                batch_size_reductions=memory_state.batch_size_reductions,
                min_batch_size_used=memory_state.min_batch_size_used,
                memory_decision_trace=memory_state.decision_trace_dicts(),
            )
