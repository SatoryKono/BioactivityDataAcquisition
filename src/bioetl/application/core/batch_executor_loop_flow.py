"""Execution-order helpers for batch extraction loops."""

from __future__ import annotations

__all__ = [
    "build_start_index",
    "flush_batch_if_needed",
    "flush_remaining_batch",
    "process_extracted_record_iteration",
]

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_executor_loop_progress import (
    _BatchCheckpointRecoveryProtocol,
    _BatchProgressReporterProtocol,
    _BatchProgressSnapshot,
    ensure_extraction_not_shutdown,
    report_batch_progress,
    save_periodic_checkpoint_for_loop,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService

class _BatchLoopStateProtocol(Protocol):
    current_batch_size: int
    batch: list[BronzeRecord]

class _BatchStateUpdater(Protocol):
    def __call__(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> Awaitable[None]: ...

class _BatchFlushContextProtocol(Protocol):
    process_batch: _BatchStateUpdater
    memory_manager: BatchMemoryManagerService
    progress_service: _BatchProgressReporterProtocol
    progress_state: _BatchProgressSnapshot

class _BatchIterationContextProtocol(_BatchFlushContextProtocol, Protocol):
    checkpoint_recovery_service: _BatchCheckpointRecoveryProtocol
    resume_offset: int
    checkpoint_interval: int

def build_start_index(*, records_fetched: int, batch: list[BronzeRecord]) -> int:
    """Build absolute start index for the current batch buffer."""
    return records_fetched - len(batch)

async def flush_batch_if_needed(
    *,
    loop_state: _BatchLoopStateProtocol,
    records_fetched: int,
    flush_context: _BatchFlushContextProtocol,
) -> None:
    """Flush the current batch when the adaptive size threshold is reached."""
    if len(loop_state.batch) < loop_state.current_batch_size:
        return
    await flush_context.process_batch(
        loop_state.batch,
        build_start_index(
            records_fetched=records_fetched,
            batch=loop_state.batch,
        ),
    )
    loop_state.batch = []
    loop_state.current_batch_size = flush_context.memory_manager.maybe_recover(
        loop_state.current_batch_size
    )
    report_batch_progress(
        progress_service=flush_context.progress_service,
        state=flush_context.progress_state,
    )

async def flush_remaining_batch(
    *,
    loop_state: _BatchLoopStateProtocol,
    records_fetched: int,
    process_batch: _BatchStateUpdater,
) -> None:
    """Flush the remaining buffered batch after extraction completes."""
    if not loop_state.batch:
        return
    await process_batch(
        loop_state.batch,
        build_start_index(
            records_fetched=records_fetched,
            batch=loop_state.batch,
        ),
    )

async def process_extracted_record_iteration(
    *,
    loop_state: _BatchLoopStateProtocol,
    raw_record: BronzeRecord,
    shutdown_requested: bool,
    records_fetched: int,
    update_batch_size: Callable[[int], int],
    iteration_context: _BatchIterationContextProtocol,
) -> int:
    """Run one extraction-loop iteration in the canonical execution order."""
    await ensure_extraction_not_shutdown(
        shutdown_requested=shutdown_requested,
        checkpoint_recovery_service=iteration_context.checkpoint_recovery_service,
        records_fetched=records_fetched,
        resume_offset=iteration_context.resume_offset,
    )
    next_records_fetched = records_fetched + 1
    loop_state.batch.append(raw_record)
    loop_state.current_batch_size = update_batch_size(next_records_fetched)
    report_batch_progress(
        progress_service=iteration_context.progress_service,
        state=iteration_context.progress_state,
    )
    await flush_batch_if_needed(
        loop_state=loop_state,
        records_fetched=next_records_fetched,
        flush_context=iteration_context,
    )
    await save_periodic_checkpoint_for_loop(
        checkpoint_recovery_service=iteration_context.checkpoint_recovery_service,
        records_fetched=next_records_fetched,
        resume_offset=iteration_context.resume_offset,
        checkpoint_interval=iteration_context.checkpoint_interval,
    )
    return next_records_fetched
