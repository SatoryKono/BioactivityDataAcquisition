"""Internal helper functions for batch extraction loop orchestration."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_executor_loop_flow import (
    build_start_index as build_start_index_from_flow,
)
from bioetl.application.core.batch_executor_loop_flow import (
    flush_batch_if_needed as flush_batch_if_needed_from_flow,
)
from bioetl.application.core.batch_executor_loop_flow import (
    flush_remaining_batch as flush_remaining_batch_from_flow,
)
from bioetl.application.core.batch_executor_loop_flow import (
    process_extracted_record_iteration as process_extracted_record_iteration_from_flow,
)
from bioetl.application.core.batch_executor_loop_progress import (
    _BatchCheckpointRecoveryProtocol,
    _BatchProgressReporterProtocol,
    _BatchProgressSnapshot,
    build_batch_progress_payload,
    build_periodic_checkpoint_payload,
    build_shutdown_checkpoint_payload,
    ensure_extraction_not_shutdown,
    report_batch_progress,
    save_periodic_checkpoint_for_loop,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService


__all__ = [
    "BatchExtractionIterationContext",
    "BatchExtractionLoopState",
    "append_record_and_update_batch_size",
    "build_batch_progress_payload",
    "build_periodic_checkpoint_payload",
    "build_shutdown_checkpoint_payload",
    "build_start_index",
    "create_batch_extraction_loop_state",
    "ensure_extraction_not_shutdown",
    "flush_batch_if_needed",
    "flush_remaining_batch",
    "process_extracted_record_iteration",
    "report_batch_progress",
    "reset_batch_after_flush",
    "save_periodic_checkpoint_for_loop",
    "should_flush_batch",
]


@dataclass(slots=True)
class BatchExtractionLoopState:
    """Mutable state held across the extraction loop."""

    current_batch_size: int
    check_interval: int
    batch: list[BronzeRecord] = field(default_factory=list)


@dataclass(slots=True)
class BatchExtractionIterationContext:
    """Shared collaborators and counters for one extraction-loop iteration."""

    checkpoint_recovery_service: _BatchCheckpointRecoveryProtocol
    resume_offset: int
    process_batch: _BatchStateUpdater
    memory_manager: BatchMemoryManagerService
    progress_service: _BatchProgressReporterProtocol
    progress_state: _BatchProgressSnapshot
    checkpoint_interval: int


@dataclass(slots=True)
class _BatchFlushContext:
    """Concrete flush context passed into flow helpers."""

    process_batch: _BatchStateUpdater
    memory_manager: BatchMemoryManagerService
    progress_service: _BatchProgressReporterProtocol
    progress_state: _BatchProgressSnapshot


class _BatchStateUpdater(Protocol):
    """Async batch processing callback used by extraction loop helpers."""

    def __call__(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> Awaitable[None]: ...


def create_batch_extraction_loop_state(
    *,
    batch_size: int,
    check_interval: int,
) -> BatchExtractionLoopState:
    """Create extraction loop state with initial sizing parameters."""
    return BatchExtractionLoopState(
        current_batch_size=batch_size,
        check_interval=check_interval,
    )


def append_record_and_update_batch_size(
    *,
    loop_state: BatchExtractionLoopState,
    raw_record: BronzeRecord,
    memory_manager: BatchMemoryManagerService,
    records_fetched: int,
) -> None:
    """Append one raw record and update adaptive batch size if needed."""
    loop_state.batch.append(raw_record)
    loop_state.current_batch_size = memory_manager.check_pressure(
        loop_state.current_batch_size,
        loop_state.check_interval,
        records_fetched,
    )


def should_flush_batch(loop_state: BatchExtractionLoopState) -> bool:
    """Return whether the accumulated batch reached the current flush size."""
    return len(loop_state.batch) >= loop_state.current_batch_size


def reset_batch_after_flush(
    *,
    loop_state: BatchExtractionLoopState,
    memory_manager: BatchMemoryManagerService,
) -> None:
    """Reset batch buffer and let adaptive sizing recover if pressure eased."""
    loop_state.batch = []
    loop_state.current_batch_size = memory_manager.maybe_recover(
        loop_state.current_batch_size
    )


def build_start_index(*, records_fetched: int, batch: list[BronzeRecord]) -> int:
    """Build absolute start index for the current batch buffer."""
    return build_start_index_from_flow(records_fetched=records_fetched, batch=batch)


async def flush_batch_if_needed(
    *,
    loop_state: BatchExtractionLoopState,
    records_fetched: int,
    process_batch: _BatchStateUpdater,
    memory_manager: BatchMemoryManagerService,
    progress_service: _BatchProgressReporterProtocol,
    progress_state: _BatchProgressSnapshot,
) -> None:
    """Flush the current batch when adaptive size threshold is reached."""
    await flush_batch_if_needed_from_flow(
        loop_state=loop_state,
        records_fetched=records_fetched,
        flush_context=_BatchFlushContext(
            process_batch=process_batch,
            memory_manager=memory_manager,
            progress_service=progress_service,
            progress_state=progress_state,
        ),
    )


async def flush_remaining_batch(
    *,
    loop_state: BatchExtractionLoopState,
    records_fetched: int,
    process_batch: _BatchStateUpdater,
) -> None:
    """Flush the remaining buffered batch after extraction completes."""
    await flush_remaining_batch_from_flow(
        loop_state=loop_state,
        records_fetched=records_fetched,
        process_batch=process_batch,
    )


def _update_batch_size_for_iteration(
    *,
    loop_state: BatchExtractionLoopState,
    memory_manager: BatchMemoryManagerService,
    records_fetched: int,
) -> int:
    """Compute the next adaptive batch size during one loop iteration."""
    return memory_manager.check_pressure(
        loop_state.current_batch_size,
        loop_state.check_interval,
        records_fetched,
    )


async def process_extracted_record_iteration(
    *,
    loop_state: BatchExtractionLoopState,
    raw_record: BronzeRecord,
    shutdown_requested: bool,
    records_fetched: int,
    iteration_context: BatchExtractionIterationContext,
) -> int:
    """Run one extraction-loop iteration in the canonical execution order."""
    return await process_extracted_record_iteration_from_flow(
        loop_state=loop_state,
        raw_record=raw_record,
        shutdown_requested=shutdown_requested,
        records_fetched=records_fetched,
        update_batch_size=lambda next_records_fetched: _update_batch_size_for_iteration(
            loop_state=loop_state,
            memory_manager=iteration_context.memory_manager,
            records_fetched=next_records_fetched,
        ),
        iteration_context=iteration_context,
    )
