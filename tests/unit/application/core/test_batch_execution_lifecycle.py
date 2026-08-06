"""Unit tests for batch_execution lifecycle and run-service finalization (#7778)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.core.batch_execution.lifecycle import (
    BatchExecutionContext,
    BatchExecutionLifecycleService,
    prepare_execution_context,
)
from bioetl.application.core.batch_execution.run_service import BatchExecutionRunService
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError


class _Counters:
    records_fetched = 10
    records_bronze = 9
    records_silver = 8
    records_gold = 7
    records_gold_excluded_by_contract = 0
    records_quarantined = 1


class _Memory:
    batch_size_reductions = 0
    min_batch_size_used = 100

    def decision_trace_dicts(self) -> tuple[dict[str, Any], ...]:
        return ()


@pytest.fixture
def lifecycle_deps() -> tuple[MagicMock, MagicMock, MagicMock]:
    progress = MagicMock()
    progress.initialize_tracking = AsyncMock()
    tracing = MagicMock()
    tracing.start_execution_span.return_value = MagicMock(name="span")
    tracing.set_execution_stats = MagicMock()
    tracing.end_span = MagicMock()
    tracing.end_span_with_shutdown = MagicMock()
    checkpoint = MagicMock()
    checkpoint.save_checkpoint_on_exception = AsyncMock()
    checkpoint.save_checkpoint_on_shutdown = AsyncMock()
    return progress, tracing, checkpoint


def test_prepare_execution_context_sets_resume_offset() -> None:
    ctx = prepare_execution_context(limit=5, query="q", offset=3)
    assert ctx == BatchExecutionContext(
        limit=5, query="q", offset=3, resume_offset=3
    )


@pytest.mark.asyncio
async def test_start_execution_initializes_progress_and_span(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    execution_context = prepare_execution_context(limit=10, query=None, offset=None)
    lifecycle = await service.start_execution(execution_context)
    progress.initialize_tracking.assert_awaited_once_with(10)
    tracing.start_execution_span.assert_called_once()
    assert lifecycle.execution_context is execution_context
    assert lifecycle.root_span is tracing.start_execution_span.return_value


@pytest.mark.asyncio
async def test_finalize_execution_success_sets_stats_and_ends_span(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    execution_context = prepare_execution_context(limit=None, query=None, offset=2)
    lifecycle = await service.start_execution(execution_context)
    await service.finalize_execution(
        _Counters(),
        lifecycle,
        batch_size_reductions=1,
        min_batch_size_used=50,
        memory_decision_trace=(),
    )
    tracing.set_execution_stats.assert_called_once()
    tracing.end_span.assert_called_once_with(lifecycle.root_span)
    checkpoint.save_checkpoint_on_shutdown.assert_not_awaited()
    checkpoint.save_checkpoint_on_exception.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_execution_shutdown_saves_checkpoint(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    lifecycle = await service.start_execution(
        prepare_execution_context(limit=None, query=None, offset=0)
    )
    await service.finalize_execution(
        _Counters(),
        lifecycle,
        batch_size_reductions=0,
        min_batch_size_used=100,
        memory_decision_trace=(),
        shutdown=True,
    )
    checkpoint.save_checkpoint_on_shutdown.assert_awaited_once()
    tracing.end_span_with_shutdown.assert_called_once_with(lifecycle.root_span)


@pytest.mark.asyncio
async def test_finalize_execution_error_saves_exception_checkpoint(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    lifecycle = await service.start_execution(
        prepare_execution_context(limit=None, query=None, offset=0)
    )
    err = RuntimeError("boom")
    await service.finalize_execution(
        _Counters(),
        lifecycle,
        batch_size_reductions=0,
        min_batch_size_used=100,
        memory_decision_trace=(),
        error=err,
    )
    checkpoint.save_checkpoint_on_exception.assert_awaited_once()
    tracing.end_span.assert_called_once_with(lifecycle.root_span, err)


@pytest.mark.asyncio
async def test_run_service_finalizes_on_cancelled_error(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    lifecycle_service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    run_service = BatchExecutionRunService(
        execution_lifecycle_service=lifecycle_service
    )
    execution_context = prepare_execution_context(limit=1, query=None, offset=0)

    async def _cancel_loop(execution_context: BatchExecutionContext) -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await run_service.execute(
            execution_context=execution_context,
            run_loop=_cancel_loop,
            execution_state=_Counters(),
            memory_state=_Memory(),
        )
    checkpoint.save_checkpoint_on_shutdown.assert_awaited_once()
    tracing.end_span_with_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_run_service_finalizes_on_pipeline_shutdown(
    lifecycle_deps: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    progress, tracing, checkpoint = lifecycle_deps
    lifecycle_service = BatchExecutionLifecycleService(
        progress_service=progress,
        tracing_manager=tracing,
        checkpoint_recovery_service=checkpoint,
    )
    run_service = BatchExecutionRunService(
        execution_lifecycle_service=lifecycle_service
    )
    execution_context = prepare_execution_context(limit=1, query=None, offset=0)

    async def _shutdown_loop(execution_context: BatchExecutionContext) -> None:
        raise PipelineShutdownError("stop")

    with pytest.raises(PipelineShutdownError):
        await run_service.execute(
            execution_context=execution_context,
            run_loop=_shutdown_loop,
            execution_state=_Counters(),
            memory_state=_Memory(),
        )
    checkpoint.save_checkpoint_on_shutdown.assert_awaited_once()
