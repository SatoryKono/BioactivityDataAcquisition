"""Execution-state application service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExecutionStateService"]


from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.application.core.batch_execution.contracts import (
    BatchExecutionStateProtocol,
    BatchExecutionStatisticsState,
    BatchResultBuilderProtocol,
)
from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_batch_result_snapshot,
    build_processed_batch_outcome,
    build_run_statistics,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_processing_contracts import (
        BatchProcessingOutcome,
    )
    from bioetl.domain.types import BronzeRecord

_BatchResultT = TypeVar("_BatchResultT", covariant=True)


class BatchExecutionStateService:
    """Pure service applying processed batch outcomes to executor state."""

    def __init__(self) -> None:
        """Initialize state service."""
        pass

    def commit_successful_batch(
        self,
        *,
        state: object,
        records: list[BronzeRecord],
        outcome: BatchProcessingOutcome,
    ) -> None:
        """Apply one successful batch outcome to executor-level state."""
        apply_processed_batch_outcome(
            state=cast(BatchExecutionStateProtocol, state),
            outcome=build_processed_batch_outcome(
                records=records,
                output=outcome,
            ),
        )

    def build_batch_result(
        self,
        *,
        state: object,
        batch_result_type: BatchResultBuilderProtocol[_BatchResultT],
    ) -> _BatchResultT:
        """Project current cumulative counters into public batch result."""
        typed_state = cast(BatchExecutionStatisticsState, state)
        batch_result = build_batch_result_snapshot(
            batch_result_type=batch_result_type,
            records_bronze=typed_state.records_bronze,
            records_silver=typed_state.records_silver,
            records_gold=typed_state.records_gold,
            records_quarantined=typed_state.records_quarantined,
        )
        return batch_result

    def build_run_statistics(
        self,
        *,
        state: object,
    ) -> dict[str, int | list[str]]:
        """Project deterministic run statistics from current executor state."""
        typed_state = cast(BatchExecutionStatisticsState, state)
        statistics = build_run_statistics(
            records_fetched=typed_state.records_fetched,
            records_bronze=typed_state.records_bronze,
            records_silver=typed_state.records_silver,
            records_gold=typed_state.records_gold,
            records_gold_excluded_by_contract=(
                typed_state.records_gold_excluded_by_contract
            ),
            records_quarantined=typed_state.records_quarantined,
            records_filtered_out=typed_state.records_filtered_out,
            source_batch_ids=typed_state._source_batch_ids,
        )
        return statistics
