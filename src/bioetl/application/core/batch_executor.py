"""Unified Batch Executor for ETL pipeline orchestration."""

from __future__ import annotations

__all__ = ["BatchExecutor", "BatchResult"]


from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_execution_lifecycle import (
    BatchExecutionContext,
    prepare_execution_context,
)
from bioetl.application.core.batch_execution_run_service import (
    BatchExecutionRunService,
)
from bioetl.application.core.batch_execution_state_service import (
    BatchExecutionStateService,
)
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.domain.constants import (
    DEFAULT_CHECKPOINT_INTERVAL as _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL,
)
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
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


class BatchExecutor(_BatchExecutorDQMixin):
    """Unified executor for ETL batches: fetch -> transform -> write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_CHECKPOINT_INTERVAL = _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL

    def __init__(
        self,
        services: PipelineService,
        context: PipelineContext,
        config: RecordProcessorConfig,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        memory_manager: BatchMemoryManagerService,
        execution_run_service: BatchExecutionRunService,
        extraction_loop_service: BatchExtractionLoopService,
        execution_state_service: BatchExecutionStateService,
        *,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize batch executor.

        Args:
            services: Shared pipeline services (logger, DQ report service, etc.).
            context: Pipeline-level context carrying run metadata and identifiers.
            config: Record processor configuration (entity type, table names, DQ config).
            batch_metrics: Recorder for per-batch and per-run metrics.
            transformer: Handles Bronze→Silver→Gold record transformation.
            writer: Writes transformed records to storage layers.
            memory_manager: Monitors memory pressure and adjusts batch sizing.
            execution_run_service: Coordinates start/finalize lifecycle for one run.
            extraction_loop_service: Drives the async record extraction loop.
            execution_state_service: Applies processed-batch outcomes to executor state.
            batch_size: Initial number of records per batch; defaults to DEFAULT_BATCH_SIZE.
            checkpoint_interval: Number of records between checkpoint saves; defaults to domain default.
            logger: Logger override; falls back to services.logger if not provided.
        """
        self._services = services
        self._context = context
        self._config = config
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

        # Kept for compatibility and test visibility; execution services use them upstream.
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer

        self._execution_run_service = execution_run_service
        self._extraction_loop_service = extraction_loop_service
        self._execution_state_service = execution_state_service
        # Retained compatibility seam for tests/helpers that still inspect the
        # delegated batch-processing service through BatchExecutor directly.
        self._batch_processing_service = (
            self._execution_state_service._batch_processing_service
        )

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
        execution_context = self._prepare_execution_context(
            limit=limit,
            query=query,
            offset=offset,
        )
        await self._execution_run_service.execute(
            execution_context=execution_context,
            run_loop=self._run_extraction_loop,
            execution_state=self,
            memory_state=self._memory,
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
        """Public API for processing one explicit batch."""
        await self._process_batch_and_update_state(records, start_index)
        return self._execution_state_service.build_batch_result(
            state=self,
            batch_result_type=BatchResult,
        )

    async def _process_batch_and_update_state(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> None:
        """Process one batch and apply results to executor-level counters/state."""
        await self._execution_state_service.process_batch_and_update_state(
            state=self,
            records=records,
            start_index=start_index,
            query_string=self._query_string,
        )

    def get_run_statistics(self) -> dict[str, int | list[str]]:
        """Get aggregated statistics for the entire pipeline run."""
        return self._execution_state_service.build_run_statistics(
            state=self,
        )
