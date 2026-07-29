# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
# RuntimeState properties own dual-declared DQ fields (PD2-7).
"""Unified Batch Executor for ETL pipeline orchestration."""

from __future__ import annotations

__all__ = ["BatchExecutor", "BatchResult"]

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_execution import (
    BatchExecutionContext,
    BatchExecutionRunService,
)
from bioetl.application.core.batch_executor_dq_mixin import _BatchExecutorDQMixin
from bioetl.application.core.batch_executor_protocols import (
    BatchStateCommitProtocol,
    PipelineProcessingProtocol,
)
from bioetl.application.core.batch_executor_runtime_state import (
    BatchExecutorRuntimeState,
    BatchExecutorRuntimeStateMixin,
)
from bioetl.application.core.batch_executor_state_flow import (
    execute_batch_run,
    prepare_batch_execution_context,
    process_explicit_batch,
    process_stateful_batch,
)
from bioetl.application.core.batch_extraction_loop_service import (
    BatchExtractionLoopService,
)
from bioetl.application.core.batch_runtime_failure_policy import (
    PIPELINE_EXECUTION_ERRORS as _RF005_SHARED_FAILURE_POLICY,
)
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionEvent,
    BatchExecutionFSM,
    BatchExecutionState,
)
from bioetl.domain.constants import (
    DEFAULT_CHECKPOINT_INTERVAL as _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL,
)
from bioetl.domain.types import BronzeRecord, JsonDict

_SHARED_FAILURE_POLICY = _RF005_SHARED_FAILURE_POLICY

if TYPE_CHECKING:
    from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
    from bioetl.application.core.pipeline_aux_service_protocols import (
        PipelineExecutionServicesProtocol,
    )
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort

@dataclass(frozen=True, slots=True)
class BatchExecutorDependencies:
    """Grouped collaborators required by BatchExecutor."""

    memory_manager: BatchMemoryManagerService
    execution_run_service: BatchExecutionRunService
    extraction_loop_service: BatchExtractionLoopService
    execution_state_service: BatchStateCommitProtocol
    processing_port: PipelineProcessingProtocol
    fsm: BatchExecutionFSM
    runtime_state_factory: Callable[[], BatchExecutorRuntimeState] = (
        BatchExecutorRuntimeState
    )

@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int

class BatchExecutor(BatchExecutorRuntimeStateMixin, _BatchExecutorDQMixin):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Unified executor for ETL batches: fetch -> transform -> write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_CHECKPOINT_INTERVAL = _DOMAIN_DEFAULT_CHECKPOINT_INTERVAL

    def __init__(
        self,
        services: PipelineExecutionServicesProtocol,
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
        self._runtime_state = dependencies.runtime_state_factory()

        self._execution_run_service = dependencies.execution_run_service
        self._extraction_loop_service = dependencies.extraction_loop_service
        self._execution_state_service = dependencies.execution_state_service
        self._processing_port = dependencies.processing_port
        self._fsm = dependencies.fsm
        self._fsm_state = BatchExecutionState.IDLE
        self._batch_result_type = BatchResult
        self._debug_export_service = getattr(
            dependencies.processing_port,
            "debug_export_service",
            None,
        )

    @property
    def entity_type(self) -> str:
        """Get entity type being processed."""
        return self._config.entity_type

    async def execute(
        self, limit: int | None, query: str | None = None, offset: int | None = None
    ) -> None:
        """Execute the pipeline for the provided limit/query/offset inputs."""
        await execute_batch_run(
            self,  # pyright: ignore[reportArgumentType]
            limit=limit,
            query=query,
            offset=offset,
        )

    def _prepare_execution_context(
        self, *, limit: int | None, query: str | None, offset: int | None
    ) -> BatchExecutionContext:
        """Persist execution-scoped inputs and return the explicit loop context."""
        return prepare_batch_execution_context(
            self,  # pyright: ignore[reportArgumentType]
            limit=limit,
            query=query,
            offset=offset,
        )

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
            progress_state=self,  # pyright: ignore[reportArgumentType]
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
        return await process_explicit_batch(self, records, start_index)  # pyright: ignore[reportArgumentType]

    async def _process_batch_and_update_state(
        self,
        records: list[BronzeRecord],
        start_index: int,
    ) -> None:
        """Process one batch and apply results to executor-level counters/state."""
        await process_stateful_batch(self, records, start_index)  # pyright: ignore[reportArgumentType]

    def get_run_statistics(self) -> dict[str, int | list[str]]:
        """Get aggregated statistics for the entire pipeline run."""
        return self._execution_state_service.build_run_statistics(
            state=self,
        )

    @property
    def debug_export_result(self) -> object | None:
        """Return the persisted debug export result when available."""
        return self._debug_export_result

    async def finalize_debug_export(
        self,
        *,
        status: str,
        manifest_id: str | None,
    ) -> object | None:
        """Persist the debug export audit pack once per run when enabled."""
        if self._debug_export_service is None:
            return None
        if self._debug_export_result is not None:
            return self._debug_export_result
        self._debug_export_result = await asyncio.to_thread(
            self._debug_export_service.finalize,
            status=status,
            manifest_id=manifest_id,
        )
        return self._debug_export_result

    @property
    def execution_diagnostics(self) -> JsonDict:
        """Return bounded adaptive-memory diagnostics for run-history consumers."""
        trace = self._memory.decision_trace_dicts()
        if not trace:
            return {}
        return {
            "adaptive_memory": {
                "enabled": bool(self._memory.enabled),
                "decision_count": len(trace),
                "batch_size_reductions": int(self._memory.batch_size_reductions),
                "min_batch_size_used": int(self._memory.min_batch_size_used),
                "decision_trace": trace,
            }
        }
