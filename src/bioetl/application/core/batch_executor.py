"""Unified Batch Executor for ETL pipeline orchestration."""

from __future__ import annotations

__all__ = ["BatchExecutor", "BatchResult"]


from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_execution_lifecycle import (
    BatchExecutionContext,
    BatchExecutionLifecycleContext,
    BatchExecutionLifecycleService,
    prepare_execution_context,
)
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_batch_result_snapshot,
    build_processed_batch_outcome,
    build_run_statistics,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
    BatchProcessingServicePort,
)
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.constants import (
    DEFAULT_CHECKPOINT_INTERVAL as _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
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


class _BatchProcessingStateUpdaterPort(BatchProcessingServicePort, Protocol):
    """Processing contract required by BatchExecutor across loop and batch update."""

    async def process_batch(
        self,
        *,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> BatchProcessingOutput: ...
class BatchExecutor(_BatchExecutorDQMixin):
    """Unified executor for ETL batches: fetch -> transform -> write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_CHECKPOINT_INTERVAL = _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL
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
        batch_processing_service: _BatchProcessingStateUpdaterPort,
        execution_lifecycle_service: BatchExecutionLifecycleService,
        extraction_loop_service: BatchExtractionLoopService,
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
        self._execution_lifecycle = execution_lifecycle_service
        self._extraction_loop_service = extraction_loop_service

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
            await self._execution_lifecycle.finalize_execution(
                self,
                lifecycle_context,
                batch_size_reductions=self._memory.batch_size_reductions,
                min_batch_size_used=self._memory.min_batch_size_used,
                shutdown=True,
            )
            raise
        except self._PIPELINE_EXECUTION_ERRORS as error:
            await self._execution_lifecycle.finalize_execution(
                self,
                lifecycle_context,
                batch_size_reductions=self._memory.batch_size_reductions,
                min_batch_size_used=self._memory.min_batch_size_used,
                error=error,
            )
            raise
        else:
            await self._execution_lifecycle.finalize_execution(
                self,
                lifecycle_context,
                batch_size_reductions=self._memory.batch_size_reductions,
                min_batch_size_used=self._memory.min_batch_size_used,
            )

    async def _start_execution(
        self, *, limit: int | None, query: str | None, offset: int | None
    ) -> BatchExecutionLifecycleContext:
        """Initialize progress tracking and tracing for one executor run."""
        execution_context = self._prepare_execution_context(
            limit=limit, query=query, offset=offset
        )
        return await self._execution_lifecycle.start_execution(
            execution_context=execution_context,
        )

    def _prepare_execution_context(
        self, *, limit: int | None, query: str | None, offset: int | None
    ) -> BatchExecutionContext:
        """Persist execution-scoped inputs and return the explicit loop context."""
        execution_context = prepare_execution_context(
            limit=limit,
            query=query,
            offset=offset,
        )
        self._resume_offset = execution_context.resume_offset
        self._query_string = execution_context.query
        return execution_context

    async def _run_extraction_loop(
        self,
        execution_context: BatchExecutionContext,
    ) -> None:
        """Run the main extraction and processing loop."""
        await self._extraction_loop_service.run(
            execution_context,
            batch_size=self.batch_size,
            process_batch=self._process_batch_and_update_state,
            progress_state=self,
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
