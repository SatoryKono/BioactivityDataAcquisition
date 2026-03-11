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
    BatchExecutionStateOutcome,
    build_batch_execution_state_update,
    build_run_statistics,
)
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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
        self,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> None:
        """Execute the pipeline: fetch -> transform -> write.

        Args:
            limit: Maximum number of records to fetch, or None for all available.
            query: Optional query string forwarded to the data source.
            offset: Optional starting offset for resuming a previous run.
        """
        self._resume_offset = offset or 0
        self._query_string = query
        await self._progress_service.initialize_tracking(limit)

        root_span = self._tracing.start_execution_span()

        try:
            await self._run_extraction_loop(limit, query, offset=offset)
            self._tracing.set_execution_stats(
                root_span,
                total_fetched=self.records_fetched,
                total_bronze=self.records_bronze,
                total_silver=self.records_silver,
                total_gold=self.records_gold,
                total_quarantined=self.records_quarantined,
                batch_size_reductions=self._memory.batch_size_reductions,
                min_batch_size_used=self._memory.min_batch_size_used,
            )
        except PipelineShutdownError:
            await self._checkpoint_recovery_service.save_checkpoint_on_shutdown(
                records_fetched=self.records_fetched,
                resume_offset=self._resume_offset,
            )
            self._tracing.end_span_with_shutdown(root_span)
            raise
        except self._PIPELINE_EXECUTION_ERRORS as error:
            await self._checkpoint_recovery_service.save_checkpoint_on_exception(
                records_fetched=self.records_fetched,
                resume_offset=self._resume_offset,
                error=error,
            )
            self._tracing.end_span(root_span, error)
            raise
        else:
            self._tracing.end_span(root_span)

    async def _run_extraction_loop(
        self,
        limit: int | None,
        query: str | None,
        offset: int | None = None,
    ) -> None:
        """Run the main extraction and processing loop."""
        batch: list[BronzeRecord] = []
        current_batch_size = self.batch_size
        check_interval = self._memory.get_check_interval()

        async for raw_record in self._batch_processing_service.extract_records(
            limit=limit,
            query=query,
            offset=offset,
        ):
            if self._shutdown_signal.is_requested:
                await self._checkpoint_recovery_service.save_checkpoint_now(
                    records_fetched=self.records_fetched,
                    resume_offset=self._resume_offset,
                )
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            self.records_fetched += 1
            self._progress_service.report_progress(
                records_fetched=self.records_fetched,
                records_bronze=self.records_bronze,
                records_silver=self.records_silver,
                records_filtered_out=self.records_filtered_out,
            )

            current_batch_size = self._memory.check_pressure(
                current_batch_size,
                check_interval,
                self.records_fetched,
            )

            if len(batch) >= current_batch_size:
                start_index = self.records_fetched - len(batch)
                await self._process_batch_and_update_state(batch, start_index)
                batch = []
                current_batch_size = self._memory.maybe_recover(current_batch_size)
                self._progress_service.report_progress(
                    records_fetched=self.records_fetched,
                    records_bronze=self.records_bronze,
                    records_silver=self.records_silver,
                    records_filtered_out=self.records_filtered_out,
                )

            await self._checkpoint_recovery_service.save_periodic_checkpoint(
                records_fetched=self.records_fetched,
                resume_offset=self._resume_offset,
                checkpoint_interval=self.checkpoint_interval,
            )

        if batch:
            start_index = self.records_fetched - len(batch)
            await self._process_batch_and_update_state(batch, start_index)

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
        return BatchResult(
            bronze_count=self.records_bronze,
            silver_count=self.records_silver,
            gold_count=self.records_gold,
            quarantined_count=self.records_quarantined,
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
        self._apply_batch_state_update(
            build_batch_execution_state_update(
                input_record_count=len(records),
                output=output,
            )
        )

        if self._should_collect_dq_data():
            self._collect_dq_data(
                records=records,
                batch_id=output.batch_id,
                bronze_result=output.bronze_result,
                silver_records=output.silver_records,
                gold_records=output.gold_records,
            )

    def _apply_batch_state_update(
        self, state_update: BatchExecutionStateOutcome
    ) -> None:
        """Apply one batch of counter deltas to executor-level state."""
        self.records_bronze += state_update.bronze_count
        self.records_silver += state_update.silver_count
        self.records_gold += state_update.gold_count
        self.records_quarantined += state_update.quarantined_count
        self.records_filtered_out += state_update.filtered_out_count
        self._source_batch_ids.append(state_update.source_batch_id)

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
