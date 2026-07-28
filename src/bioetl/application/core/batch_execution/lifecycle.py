"""Execution lifecycle orchestration for BatchExecutor runtime."""

from __future__ import annotations

__all__ = [
    "BatchExecutionContext",
    "BatchExecutionFinalizationContext",
    "BatchExecutionLifecycleContext",
    "BatchExecutionLifecycleService",
    "prepare_execution_context",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_execution.contracts import (
    BatchExecutionCountersSnapshot,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

@dataclass(frozen=True, slots=True)
class BatchExecutionContext:
    """Execution-scoped inputs shared across the batch executor loop."""

    limit: int | None
    query: str | None
    offset: int | None
    resume_offset: int

@dataclass(frozen=True, slots=True)
class BatchExecutionLifecycleContext:
    """Top-level execution state shared across success and failure handlers."""

    execution_context: BatchExecutionContext
    root_span: Span | None

@dataclass(frozen=True, slots=True)
class BatchExecutionFinalizationContext:
    """Execution snapshot used by success, shutdown, and error finalization."""

    root_span: Span | None
    resume_offset: int
    total_fetched: int
    total_bronze: int
    total_silver: int
    total_gold: int
    total_quarantined: int
    batch_size_reductions: int
    min_batch_size_used: int
    memory_decision_trace: tuple[JsonDict, ...]

class _BatchProgressInitializerProtocol(Protocol):
    """Minimal progress initialization contract for executor lifecycle."""

    async def initialize_tracking(self, limit: int | None) -> None: ...

class _BatchCheckpointRecoveryLifecycleProtocol(Protocol):
    """Checkpoint finalization contract used by executor lifecycle."""

    async def save_checkpoint_on_exception(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
        error: BaseException,
    ) -> None: ...

    async def save_checkpoint_on_shutdown(
        self,
        *,
        records_fetched: int,
        resume_offset: int,
    ) -> None: ...

class _BatchTracingLifecycleProtocol(Protocol):
    """Tracing contract used by executor lifecycle orchestration."""

    def start_execution_span(self) -> Span | None: ...

    def set_execution_stats(
        self,
        span: Span | None,
        *,
        total_fetched: int,
        total_bronze: int,
        total_silver: int,
        total_gold: int,
        total_quarantined: int,
        batch_size_reductions: int,
        min_batch_size_used: int,
        memory_decision_trace: tuple[JsonDict, ...],
    ) -> None: ...

    def end_span(self, span: Span | None, error: Exception | None = None) -> None: ...

    def end_span_with_shutdown(self, span: Span | None) -> None: ...

def prepare_execution_context(
    *,
    limit: int | None,
    query: str | None,
    offset: int | None,
) -> BatchExecutionContext:
    """Build explicit execution context from run inputs."""
    return BatchExecutionContext(
        limit=limit,
        query=query,
        offset=offset,
        resume_offset=offset or 0,
    )

class BatchExecutionLifecycleService:
    """Coordinates executor start and finalize flows."""

    def __init__(
        self,
        *,
        progress_service: _BatchProgressInitializerProtocol,
        tracing_manager: _BatchTracingLifecycleProtocol,
        checkpoint_recovery_service: _BatchCheckpointRecoveryLifecycleProtocol,
    ) -> None:
        """Initialize execution lifecycle service."""
        self._progress_service = progress_service
        self._tracing_manager = tracing_manager
        self._checkpoint_recovery_service = checkpoint_recovery_service

    async def start_execution(
        self,
        execution_context: BatchExecutionContext,
    ) -> BatchExecutionLifecycleContext:
        """Initialize progress tracking and tracing for one executor run."""
        await self._progress_service.initialize_tracking(execution_context.limit)
        return BatchExecutionLifecycleContext(
            execution_context=execution_context,
            root_span=self._tracing_manager.start_execution_span(),
        )

    async def finalize_execution(
        self,
        execution_state: BatchExecutionCountersSnapshot,
        lifecycle_context: BatchExecutionLifecycleContext,
        *,
        batch_size_reductions: int,
        min_batch_size_used: int,
        memory_decision_trace: tuple[JsonDict, ...],
        error: Exception | None = None,
        shutdown: bool = False,
    ) -> None:
        """Finalize execution for success, shutdown, or runtime failure."""
        finalization_context = self._build_finalization_context(
            execution_state=execution_state,
            lifecycle_context=lifecycle_context,
            batch_size_reductions=batch_size_reductions,
            min_batch_size_used=min_batch_size_used,
            memory_decision_trace=memory_decision_trace,
        )
        if shutdown:
            await self._checkpoint_recovery_service.save_checkpoint_on_shutdown(
                records_fetched=finalization_context.total_fetched,
                resume_offset=finalization_context.resume_offset,
            )
            self._tracing_manager.end_span_with_shutdown(finalization_context.root_span)
            return
        if error is not None:
            await self._checkpoint_recovery_service.save_checkpoint_on_exception(
                records_fetched=finalization_context.total_fetched,
                resume_offset=finalization_context.resume_offset,
                error=error,
            )
            self._tracing_manager.end_span(finalization_context.root_span, error)
            return
        self._tracing_manager.set_execution_stats(
            finalization_context.root_span,
            total_fetched=finalization_context.total_fetched,
            total_bronze=finalization_context.total_bronze,
            total_silver=finalization_context.total_silver,
            total_gold=finalization_context.total_gold,
            total_quarantined=finalization_context.total_quarantined,
            batch_size_reductions=finalization_context.batch_size_reductions,
            min_batch_size_used=finalization_context.min_batch_size_used,
            memory_decision_trace=finalization_context.memory_decision_trace,
        )
        self._tracing_manager.end_span(finalization_context.root_span)

    @staticmethod
    def _build_finalization_context(
        *,
        execution_state: BatchExecutionCountersSnapshot,
        lifecycle_context: BatchExecutionLifecycleContext,
        batch_size_reductions: int,
        min_batch_size_used: int,
        memory_decision_trace: tuple[JsonDict, ...],
    ) -> BatchExecutionFinalizationContext:
        """Capture one immutable snapshot for execution finalization paths."""
        return BatchExecutionFinalizationContext(
            root_span=lifecycle_context.root_span,
            resume_offset=lifecycle_context.execution_context.resume_offset,
            total_fetched=execution_state.records_fetched,
            total_bronze=execution_state.records_bronze,
            total_silver=execution_state.records_silver,
            total_gold=execution_state.records_gold,
            total_quarantined=execution_state.records_quarantined,
            batch_size_reductions=batch_size_reductions,
            min_batch_size_used=min_batch_size_used,
            memory_decision_trace=memory_decision_trace,
        )
