"""Unified Batch Executor for ETL pipeline orchestration."""

from __future__ import annotations

__all__ = ["BatchExecutor", "BatchResult"]


from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_execution import (
    BatchExecutionContext,
    BatchExecutionRunService,
    prepare_execution_context,
)
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_executor_protocols import (
    BatchStateCommitPort,
    PipelineProcessingPort,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionCommand,
    BatchExecutionEvent,
    BatchExecutionFSM,
    BatchExecutionState,
)
from bioetl.domain.constants import (
    DEFAULT_CHECKPOINT_INTERVAL as _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class BatchExecutorDependencies:
    """Grouped collaborators required by BatchExecutor."""

    memory_manager: BatchMemoryManagerService
    execution_run_service: BatchExecutionRunService
    extraction_loop_service: BatchExtractionLoopService
    execution_state_service: BatchStateCommitPort
    processing_port: PipelineProcessingPort
    fsm: BatchExecutionFSM


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


_BATCH_EXECUTOR_RUNTIME_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


class BatchExecutor(_BatchExecutorDQMixin):
    """Unified executor for ETL batches: fetch -> transform -> write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_CHECKPOINT_INTERVAL = _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL

    def __init__(
        self,
        services: PipelineService,
        context: PipelineContext,
        config: RecordProcessorConfig,
        dependencies: BatchExecutorDependencies,
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
            dependencies: Preferred grouped runtime collaborators.
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

        self._memory = dependencies.memory_manager

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

        self._execution_run_service = dependencies.execution_run_service
        self._extraction_loop_service = dependencies.extraction_loop_service
        self._execution_state_service = dependencies.execution_state_service
        self._processing_port = dependencies.processing_port
        self._fsm = dependencies.fsm
        self._fsm_state = BatchExecutionState.IDLE

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

        res = self._fsm.advance(self._fsm_state, BatchExecutionEvent.RUN_STARTED)
        self._fsm_state = res.new_state

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
        if self._fsm_state == BatchExecutionState.IDLE:
            res = self._fsm.advance(self._fsm_state, BatchExecutionEvent.RUN_STARTED)
            self._fsm_state = res.new_state

        await self._extraction_loop_service.run(
            execution_context,
            batch_size=self.batch_size,
            process_batch=self._process_batch_and_update_state,
            progress_state=self,
        )

        res_done = self._fsm.advance(
            self._fsm_state, BatchExecutionEvent.STREAM_EXHAUSTED_EMPTY
        )
        self._fsm_state = res_done.new_state

    async def process(
        self,
        records: list[BronzeRecord],
        start_index: int = 0,
    ) -> BatchResult:
        """Public API for processing one explicit batch."""
        if self._fsm_state == BatchExecutionState.IDLE:
            res = self._fsm.advance(self._fsm_state, BatchExecutionEvent.RUN_STARTED)
            self._fsm_state = res.new_state

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
        t1 = self._fsm.advance(self._fsm_state, BatchExecutionEvent.BATCH_ASSEMBLED)
        self._fsm_state = t1.new_state

        if BatchExecutionCommand.PROCESS_BATCH in t1.commands:
            try:
                outcome = await self._processing_port.process_batch(
                    records=records,
                    start_index=start_index,
                    query_string=self._query_string,
                )
            except _BATCH_EXECUTOR_RUNTIME_ERRORS:
                self._fsm_state = self._fsm.advance(
                    self._fsm_state, BatchExecutionEvent.PROCESS_FAILED
                ).new_state
                raise

            t2 = self._fsm.advance(
                self._fsm_state, BatchExecutionEvent.PROCESS_SUCCEEDED
            )
            self._fsm_state = t2.new_state

            if BatchExecutionCommand.COMMIT_STATE in t2.commands:
                try:
                    self._execution_state_service.commit_successful_batch(
                        state=self,
                        records=records,
                        outcome=outcome,
                    )
                except _BATCH_EXECUTOR_RUNTIME_ERRORS:
                    self._fsm_state = self._fsm.advance(
                        self._fsm_state, BatchExecutionEvent.STATE_COMMIT_FAILED
                    ).new_state
                    raise

                t3 = self._fsm.advance(
                    self._fsm_state, BatchExecutionEvent.STATE_COMMITTED
                )
                self._fsm_state = t3.new_state

                # FSM expects CHECKPOINT decision. We delegate the actual check to the extraction loop.
                # So we simply reset the FSM back to STREAMING for the next batch.
                t4 = self._fsm.advance(
                    self._fsm_state, BatchExecutionEvent.CHECKPOINT_NOT_REQUIRED
                )
                self._fsm_state = t4.new_state

    def get_run_statistics(self) -> dict[str, int | list[str]]:
        """Get aggregated statistics for the entire pipeline run."""
        return self._execution_state_service.build_run_statistics(
            state=self,
        )
