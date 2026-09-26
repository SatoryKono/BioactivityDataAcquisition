"""Execution-state application service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExecutionStateService"]

from typing import TYPE_CHECKING

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


class BatchExecutionStateService:
    """Pure service applying processed batch outcomes to executor state."""

    def __init__(self) -> None:
        """Initialize state service."""
        pass

    def commit_successful_batch(
        self,
        *,
        state: BatchExecutionStateProtocol,
        records: list[BronzeRecord],
        outcome: BatchProcessingOutcome,
    ) -> None:
        """Apply one successful batch outcome to executor-level state."""
        apply_processed_batch_outcome(
            state=state,
            outcome=build_processed_batch_outcome(
                records=records,
                output=outcome,
            ),
        )

    def build_batch_result[BatchResultT](
        self,
        *,
        state: BatchExecutionStatisticsState,
        batch_result_type: BatchResultBuilderProtocol[BatchResultT],
    ) -> BatchResultT:
        """Project current cumulative counters into public batch result."""
        return build_batch_result_snapshot(
            batch_result_type=batch_result_type,
            records_bronze=state.records_bronze,
            records_silver=state.records_silver,
            records_gold=state.records_gold,
            records_quarantined=state.records_quarantined,
        )

    def build_run_statistics(
        self,
        *,
        state: BatchExecutionStatisticsState,
    ) -> dict[str, int | list[str]]:
        """Project deterministic run statistics from current executor state."""
        return build_run_statistics(
            records_fetched=state.records_fetched,
            records_bronze=state.records_bronze,
            records_silver=state.records_silver,
            records_gold=state.records_gold,
            records_gold_excluded_by_contract=(state.records_gold_excluded_by_contract),
            records_quarantined=state.records_quarantined,
            records_filtered_out=state.records_filtered_out,
            source_batch_ids=state.source_batch_ids,
        )
