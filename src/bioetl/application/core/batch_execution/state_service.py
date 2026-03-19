"""Execution-state application service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExecutionStateService"]


from typing import TYPE_CHECKING, Protocol, TypeVar, cast

from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_processed_batch_outcome,
    build_run_statistics,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_processing_contracts import (
        BatchProcessingOutcome,
    )
    from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord

_BatchResultT = TypeVar("_BatchResultT", covariant=True)


class _BatchResultBuilder(Protocol[_BatchResultT]):
    """Callable result factory for executor batch-result projection."""

    def __call__(
        self,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> _BatchResultT: ...


class _BatchExecutionStatePort(Protocol):
    """Mutable execution state required to apply processed-batch outcomes."""

    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int
    records_filtered_out: int
    _source_batch_ids: list[str]

    def _should_collect_dq_data(self) -> bool: ...

    def _collect_dq_data(
        self,
        *,
        records: list[BronzeRecord],
        batch_id: BatchID,
        bronze_result: object,
        silver_records: list[BronzeRecord],
        gold_records: list[GoldRecord],
    ) -> None: ...


class _BatchExecutionStatisticsState(Protocol):
    """Snapshot required to project public results and run statistics."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int
    records_filtered_out: int
    _source_batch_ids: list[str]


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
            state=cast(_BatchExecutionStatePort, state),
            outcome=build_processed_batch_outcome(
                records=records,
                output=outcome,
            ),
        )

    def build_batch_result(
        self,
        *,
        state: object,
        batch_result_type: _BatchResultBuilder[_BatchResultT],
    ) -> _BatchResultT:
        """Project current cumulative counters into public batch result."""
        typed_state = cast(_BatchExecutionStatisticsState, state)
        return batch_result_type(
            bronze_count=typed_state.records_bronze,
            silver_count=typed_state.records_silver,
            gold_count=typed_state.records_gold,
            quarantined_count=typed_state.records_quarantined,
        )

    def build_run_statistics(
        self,
        *,
        state: object,
    ) -> dict[str, int | list[str]]:
        """Project deterministic run statistics from current executor state."""
        typed_state = cast(_BatchExecutionStatisticsState, state)
        return build_run_statistics(
            records_fetched=typed_state.records_fetched,
            records_bronze=typed_state.records_bronze,
            records_silver=typed_state.records_silver,
            records_gold=typed_state.records_gold,
            records_quarantined=typed_state.records_quarantined,
            records_filtered_out=typed_state.records_filtered_out,
            source_batch_ids=typed_state._source_batch_ids,
        )
