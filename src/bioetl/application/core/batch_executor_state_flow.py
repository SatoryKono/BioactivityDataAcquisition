# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""State-transition helpers for BatchExecutor orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.batch_execution import (
    BatchExecutionRunService,
    prepare_execution_context,
)
from bioetl.application.core.batch_execution.contracts import (
    BatchExecutionCountersSnapshot,
)
from bioetl.application.core.batch_executor_protocols import (
    BatchStateCommitProtocol,
    PipelineProcessingProtocol,
)
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_runtime_failure_policy import (
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionCommand,
    BatchExecutionEvent,
    BatchExecutionFSM,
    BatchExecutionState,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_execution import BatchExecutionContext
    from bioetl.application.core.batch_execution.contracts import (
        BatchResultBuilderProtocol,
    )
    from bioetl.application.core.batch_executor import BatchResult
    from bioetl.domain.types import BronzeRecord

class _BatchExecutorHostProtocol(BatchExecutionCountersSnapshot, Protocol):
    """Host surface required by batch state-transition helpers.

    Counter fields are owned by :class:`BatchExecutionCountersSnapshot` so the
    executor protocol does not restate the shared batch counter contract.
    """

    _resume_offset: int
    _query_string: str | None
    _fsm: BatchExecutionFSM
    _fsm_state: BatchExecutionState
    _execution_run_service: BatchExecutionRunService
    _processing_port: PipelineProcessingProtocol
    _execution_state_service: BatchStateCommitProtocol
    _memory: BatchMemoryManagerService
    _batch_result_type: type[BatchResult]

    async def _run_extraction_loop(
        self,
        execution_context: BatchExecutionContext,
    ) -> None: ...

__all__ = [
    "execute_batch_run",
    "prepare_batch_execution_context",
    "process_explicit_batch",
    "process_stateful_batch",
]

def prepare_batch_execution_context(
    host: _BatchExecutorHostProtocol,
    *,
    limit: int | None,
    query: str | None,
    offset: int | None,
) -> BatchExecutionContext:
    """Persist execution-scoped inputs and return the explicit loop context."""
    execution_context = prepare_execution_context(
        limit=limit,
        query=query,
        offset=offset,
    )
    host._resume_offset = execution_context.resume_offset
    host._query_string = execution_context.query
    return execution_context

async def execute_batch_run(
    host: _BatchExecutorHostProtocol,
    *,
    limit: int | None,
    query: str | None,
    offset: int | None,
) -> None:
    """Execute the pipeline for the provided limit/query/offset inputs."""
    execution_context = prepare_batch_execution_context(
        host,
        limit=limit,
        query=query,
        offset=offset,
    )

    transition = host._fsm.advance(host._fsm_state, BatchExecutionEvent.RUN_STARTED)
    host._fsm_state = transition.new_state

    await host._execution_run_service.execute(
        execution_context=execution_context,
        run_loop=host._run_extraction_loop,
        execution_state=host,
        memory_state=host._memory,
    )

async def process_explicit_batch(
    host: _BatchExecutorHostProtocol,
    records: list[BronzeRecord],
    start_index: int,
) -> BatchResult:
    """Run explicit batch processing and return the latest snapshot."""
    if host._fsm_state == BatchExecutionState.IDLE:
        transition = host._fsm.advance(host._fsm_state, BatchExecutionEvent.RUN_STARTED)
        host._fsm_state = transition.new_state

    await process_stateful_batch(host, records, start_index)
    return host._execution_state_service.build_batch_result(
        state=host,
        batch_result_type=cast(
            "BatchResultBuilderProtocol[BatchResult]",
            host._batch_result_type,
        ),
    )

async def process_stateful_batch(
    host: _BatchExecutorHostProtocol,
    records: list[BronzeRecord],
    start_index: int,
) -> None:
    """Process one batch and apply results to executor-level counters/state."""
    assembled = host._fsm.advance(host._fsm_state, BatchExecutionEvent.BATCH_ASSEMBLED)
    host._fsm_state = assembled.new_state

    if BatchExecutionCommand.PROCESS_BATCH not in assembled.commands:
        return

    try:
        outcome = await host._processing_port.process_batch(
            records=records,
            start_index=start_index,
            query_string=host._query_string,
        )
    except PIPELINE_EXECUTION_ERRORS:
        host._fsm_state = host._fsm.advance(
            host._fsm_state,
            BatchExecutionEvent.PROCESS_FAILED,
        ).new_state
        raise

    processed = host._fsm.advance(
        host._fsm_state,
        BatchExecutionEvent.PROCESS_SUCCEEDED,
    )
    host._fsm_state = processed.new_state

    if BatchExecutionCommand.COMMIT_STATE not in processed.commands:
        return

    try:
        host._execution_state_service.commit_successful_batch(
            state=host,
            records=records,
            outcome=outcome,
        )
    except PIPELINE_EXECUTION_ERRORS:
        host._fsm_state = host._fsm.advance(
            host._fsm_state,
            BatchExecutionEvent.STATE_COMMIT_FAILED,
        ).new_state
        raise

    committed = host._fsm.advance(
        host._fsm_state,
        BatchExecutionEvent.STATE_COMMITTED,
    )
    host._fsm_state = committed.new_state

    # FSM expects CHECKPOINT decision. We delegate the actual check to the
    # extraction loop, so reset back to STREAMING for the next batch.
    host._fsm_state = host._fsm.advance(
        host._fsm_state,
        BatchExecutionEvent.CHECKPOINT_NOT_REQUIRED,
    ).new_state
