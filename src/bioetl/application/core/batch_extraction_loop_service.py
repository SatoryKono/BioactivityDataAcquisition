"""Extraction-loop orchestration service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExtractionLoopService", "BatchProcessingServiceProtocol"]

from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_execution import BatchExecutionContext
from bioetl.application.core.batch_executor_loop_helpers import (
    BatchExtractionIterationContext,
    create_batch_extraction_loop_state,
    flush_remaining_batch,
    process_extracted_record_iteration,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable

    from bioetl.application.core.batch_checkpoint_recovery_service import (
        BatchCheckpointRecoveryService,
    )
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.batch_progress_service import BatchProgressService
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.domain.types import BronzeRecord

class BatchProcessingServiceProtocol(Protocol):
    """Minimal extraction contract required by loop orchestration."""

    def extract_records(
        self,
        *,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield raw Bronze records from the data source."""
        ...

class _BatchStateUpdater(Protocol):
    """Async batch processing callback used by the extraction loop."""

    def __call__(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> Awaitable[None]: ...

class _BatchProgressState(Protocol):
    """Mutable progress state consumed by loop helpers."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_filtered_out: int

class BatchExtractionLoopService:
    """Runs the canonical extraction loop for batch execution."""

    def __init__(
        self,
        *,
        batch_processing_service: BatchProcessingServiceProtocol,
        shutdown_signal: ShutdownSignal,
        memory_manager: BatchMemoryManagerService,
        progress_service: BatchProgressService,
        checkpoint_recovery_service: BatchCheckpointRecoveryService,
        checkpoint_interval: int,
    ) -> None:
        """Initialize extraction loop service.

        Args:
            batch_processing_service: Source adapter that yields raw Bronze records.
            shutdown_signal: Checked each iteration to honor graceful shutdown requests.
            memory_manager: Provides memory check interval for adaptive batch sizing.
            progress_service: Reports per-record and per-batch progress to observers.
            checkpoint_recovery_service: Persists resume offsets after each checkpoint.
            checkpoint_interval: Number of records between checkpoint saves.
        """
        self._batch_processing_service = batch_processing_service
        self._shutdown_signal = shutdown_signal
        self._memory_manager = memory_manager
        self._progress_service = progress_service
        self._checkpoint_recovery_service = checkpoint_recovery_service
        self._checkpoint_interval = checkpoint_interval

    async def run(
        self,
        execution_context: BatchExecutionContext,
        *,
        batch_size: int,
        process_batch: _BatchStateUpdater,
        progress_state: _BatchProgressState,
    ) -> None:
        """Run the main extraction and processing loop."""
        loop_state = create_batch_extraction_loop_state(
            batch_size=batch_size,
            check_interval=self._memory_manager.get_check_interval(),
        )
        iteration_context = BatchExtractionIterationContext(
            checkpoint_recovery_service=self._checkpoint_recovery_service,
            resume_offset=execution_context.resume_offset,
            process_batch=process_batch,
            memory_manager=self._memory_manager,
            progress_service=self._progress_service,
            progress_state=progress_state,
            checkpoint_interval=self._checkpoint_interval,
        )

        records = self._batch_processing_service.extract_records(
            limit=execution_context.limit,
            query=execution_context.query,
            offset=execution_context.offset,
        )
        try:
            async for raw_record in records:
                progress_state.records_fetched = (
                    await process_extracted_record_iteration(
                        loop_state=loop_state,
                        raw_record=raw_record,
                        shutdown_requested=self._shutdown_signal.is_requested,
                        records_fetched=progress_state.records_fetched,
                        iteration_context=iteration_context,
                    )
                )
        finally:
            aclose = getattr(records, "aclose", None)
            if callable(aclose):
                from collections.abc import Awaitable, Callable
                from typing import cast

                aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
                await aclose_fn()

        await flush_remaining_batch(
            loop_state=loop_state,
            records_fetched=progress_state.records_fetched,
            process_batch=process_batch,
        )
