"""Unified Batch Executor for ETL pipeline orchestration."""

from __future__ import annotations

__all__ = ["BatchExecutor", "BatchResult"]


from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_batch_result_snapshot,
    build_processed_batch_outcome,
    build_run_statistics,
)
from bioetl.application.core.batch_executor_loop_helpers import (
    BatchExtractionIterationContext,
    create_batch_extraction_loop_state,
    flush_remaining_batch,
    process_extracted_record_iteration,
)
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from opentelemetry.trace import Span

    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_processing_service import BatchProcessingOutput
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


@dataclass(frozen=True, slots=True)
class _BatchExecutionContext:
    """Execution-scoped inputs shared across the batch executor loop."""

    limit: int | None
    query: str | None
    offset: int | None
    resume_offset: int


@dataclass(frozen=True, slots=True)
class _BatchExecutionLifecycleContext:
    """Top-level execution state shared across success and failure handlers."""

    execution_context: _BatchExecutionContext
    root_span: Span | None


@dataclass(frozen=True, slots=True)
class _BatchExecutionFinalizationContext:
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


class _BatchProcessingServicePort(Protocol):
    """Minimal contract required by BatchExecutor for batch processing service."""

    def extract_records(
        self,
        *,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Yield raw Bronze records from data source.

        Args:
            limit: Maximum number of records to yield, or None for all.
            query: Optional query string forwarded to the data source.
            offset: Optional pagination offset for resuming extraction.
        """

    async def process_batch(
        self,
        *,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> BatchProcessingOutput:
        """Process one batch and return structured output.

        Args:
            records: List of raw Bronze records to process.
            start_index: Absolute record index of the first record in this batch.
            query_string: Query string used to fetch these records, for logging context.
        """


def _build_execution_finalization_context(
    executor: BatchExecutor,
    lifecycle_context: _BatchExecutionLifecycleContext,
) -> _BatchExecutionFinalizationContext:
    """Capture one immutable snapshot for execution finalization paths."""
    return _BatchExecutionFinalizationContext(
        root_span=lifecycle_context.root_span,
        resume_offset=lifecycle_context.execution_context.resume_offset,
        total_fetched=executor.records_fetched,
        total_bronze=executor.records_bronze,
        total_silver=executor.records_silver,
        total_gold=executor.records_gold,
        total_quarantined=executor.records_quarantined,
        batch_size_reductions=executor._memory.batch_size_reductions,
        min_batch_size_used=executor._memory.min_batch_size_used,
    )


async def _finalize_execution(
    executor: BatchExecutor,
    finalization_context: _BatchExecutionFinalizationContext,
    *,
    error: Exception | None = None,
    shutdown: bool = False,
) -> None:
    """Finalize execution for success, shutdown, or runtime failure."""
    if shutdown:
        await executor._checkpoint_recovery_service.save_checkpoint_on_shutdown(
            records_fetched=finalization_context.total_fetched,
            resume_offset=finalization_context.resume_offset,
        )
        executor._tracing.end_span_with_shutdown(finalization_context.root_span)
        return
    if error is not None:
        await executor._checkpoint_recovery_service.save_checkpoint_on_exception(
            records_fetched=finalization_context.total_fetched,
            resume_offset=finalization_context.resume_offset,
            error=error,
        )
        executor._tracing.end_span(finalization_context.root_span, error)
        return
    executor._tracing.set_execution_stats(
        finalization_context.root_span,
        total_fetched=finalization_context.total_fetched,
        total_bronze=finalization_context.total_bronze,
        total_silver=finalization_context.total_silver,
        total_gold=finalization_context.total_gold,
        total_quarantined=finalization_context.total_quarantined,
        batch_size_reductions=finalization_context.batch_size_reductions,
        min_batch_size_used=finalization_context.min_batch_size_used,
    )
    executor._tracing.end_span(finalization_context.root_span)


class BatchExecutor(_BatchExecutorDQMixin):
    """Unified executor for ETL batches: fetch -> transform -> write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_CHECKPOINT_INTERVAL = 1000
    _PIPELINE_EXECUTION_ERRORS = (
        BioETLError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    )

    def __init__(
        self,
        services: PipelineService,
        context: PipelineContext,
        config: RecordProcessorConfig,
        checkpoint_manager: CheckpointManagerService,
        shutdown_signal: ShutdownSignal,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        tracing_manager: BatchTracingManagerService,
        memory_manager: BatchMemoryManagerService,
        progress_service: BatchProgressService,
        checkpoint_recovery_service: BatchCheckpointRecoveryService,
        batch_processing_service: _BatchProcessingServicePort,
        *,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize batch executor."""
        self._services = services
        self._context = context
        self._config = config
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._logger = logger or services.logger

        self._initial_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.batch_size = self._initial_batch_size
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        self._memory = memory_manager

        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0
        self.records_filtered_out = 0

        self._bronze_records_for_dq: list[bytes] = []
        self._silver_records_for_dq: list[BronzeRecord] = []
        self._gold_records_for_dq: list[GoldRecord] = []
        self._dq_total_seen: int = 0
        self._source_batch_ids: list[str] = []
        self._last_bronze_path: str | None = None

        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer
        self._tracing = tracing_manager

        self._progress_service = progress_service
        self._checkpoint_recovery_service = checkpoint_recovery_service
        self._batch_processing_service = batch_processing_service

        self._resume_offset = 0
        self._query_string: str | None = None

    @property
    def entity_type(self) -> str:
        """Get entity type being processed."""
        return self._config.entity_type

    async def execute(
        self, limit: int | None, query: str | None = None, offset: int | None = None
    ) -> None:
        """Execute the pipeline for the provided limit/query/offset inputs."""
        lifecycle_context = await self._start_execution(
            limit=limit, query=query, offset=offset
        )

        try:
            await self._run_extraction_loop(lifecycle_context.execution_context)
        except PipelineShutdownError:
            await _finalize_execution(
                self,
                _build_execution_finalization_context(self, lifecycle_context),
                shutdown=True,
            )
            raise
        except self._PIPELINE_EXECUTION_ERRORS as error:
            await _finalize_execution(
                self,
                _build_execution_finalization_context(self, lifecycle_context),
                error=error,
            )
            raise
        else:
            await _finalize_execution(
                self,
                _build_execution_finalization_context(self, lifecycle_context),
            )

    async def _start_execution(
        self, *, limit: int | None, query: str | None, offset: int | None
    ) -> _BatchExecutionLifecycleContext:
        """Initialize progress tracking and tracing for one executor run."""
        execution_context = self._prepare_execution_context(
            limit=limit, query=query, offset=offset
        )
        await self._progress_service.initialize_tracking(execution_context.limit)
        return _BatchExecutionLifecycleContext(
            execution_context=execution_context,
            root_span=self._tracing.start_execution_span(),
        )

    def _prepare_execution_context(
        self, *, limit: int | None, query: str | None, offset: int | None
    ) -> _BatchExecutionContext:
        """Persist execution-scoped inputs and return the explicit loop context."""
        execution_context = _BatchExecutionContext(
            limit=limit,
            query=query,
            offset=offset,
            resume_offset=offset or 0,
        )
        self._resume_offset = execution_context.resume_offset
        self._query_string = execution_context.query
        return execution_context

    async def _run_extraction_loop(
        self,
        execution_context: _BatchExecutionContext,
    ) -> None:
        """Run the main extraction and processing loop."""
        loop_state = create_batch_extraction_loop_state(
            batch_size=self.batch_size,
            check_interval=self._memory.get_check_interval(),
        )
        iteration_context = BatchExtractionIterationContext(
            checkpoint_recovery_service=self._checkpoint_recovery_service,
            resume_offset=execution_context.resume_offset,
            process_batch=self._process_batch_and_update_state,
            memory_manager=self._memory,
            progress_service=self._progress_service,
            progress_state=self,
            checkpoint_interval=self.checkpoint_interval,
        )

        async for raw_record in self._batch_processing_service.extract_records(
            limit=execution_context.limit,
            query=execution_context.query,
            offset=execution_context.offset,
        ):
            self.records_fetched = await process_extracted_record_iteration(
                loop_state=loop_state,
                raw_record=raw_record,
                shutdown_requested=self._shutdown_signal.is_requested,
                records_fetched=self.records_fetched,
                iteration_context=iteration_context,
            )

        await flush_remaining_batch(
            loop_state=loop_state,
            records_fetched=self.records_fetched,
            process_batch=self._process_batch_and_update_state,
        )

    async def process(
        self,
        records: list[BronzeRecord],
        start_index: int = 0,
    ) -> BatchResult:
        """Public API for processing one explicit batch.

        Args:
            records: List of raw Bronze records to process.
            start_index: Absolute record index of the first record in this batch.

        Returns:
            BatchResult with cumulative bronze, silver, gold, and quarantined counts.
        """
        await self._process_batch_and_update_state(records, start_index)
        return build_batch_result_snapshot(
            batch_result_type=BatchResult,
            records_bronze=self.records_bronze,
            records_silver=self.records_silver,
            records_gold=self.records_gold,
            records_quarantined=self.records_quarantined,
        )

    async def _process_batch_and_update_state(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> None:
        """Process one batch and apply results to executor-level counters/state."""
        output = await self._batch_processing_service.process_batch(
            records=records,
            start_index=start_index,
            query_string=self._query_string,
        )
        apply_processed_batch_outcome(
            state=self,
            outcome=build_processed_batch_outcome(
                records=records,
                output=output,
            )
        )

    def get_run_statistics(self) -> dict[str, int | list[str]]:
        """Get aggregated statistics for the entire pipeline run.

        Returns:
            Dictionary with fetched, bronze, silver, gold, quarantined, filtered_out
            record counts and the deduplicated list of source batch IDs.
        """
        return build_run_statistics(
            records_fetched=self.records_fetched,
            records_bronze=self.records_bronze,
            records_silver=self.records_silver,
            records_gold=self.records_gold,
            records_quarantined=self.records_quarantined,
            records_filtered_out=self.records_filtered_out,
            source_batch_ids=self._source_batch_ids,
        )
