"""Execution-state application service for BatchExecutor runtime."""

from __future__ import annotations

__all__ = ["BatchExecutionStateService"]


from typing import TYPE_CHECKING, Protocol, TypeVar

from bioetl.application.core.batch_executor_helpers import (
    apply_processed_batch_outcome,
    build_processed_batch_outcome,
    build_run_statistics,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_processing_service import BatchProcessingOutput
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


class _BatchProcessingStateUpdaterPort(Protocol):
    """Batch-processing contract required to update executor state."""

    async def process_batch(
        self,
        *,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> BatchProcessingOutput: ...


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
    """Applies processed batch outputs to executor state and snapshots."""

    def __init__(
        self,
        *,
        batch_processing_service: _BatchProcessingStateUpdaterPort,
    ) -> None:
        """Initialize execution state service.

        Args:
            batch_processing_service: Processes one batch of Bronze records through
                Silver and Gold transformation, returning a BatchProcessingOutput.
        """
        self._batch_processing_service = batch_processing_service

    async def process_batch_and_update_state(
        self,
        *,
        state: _BatchExecutionStatePort,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> None:
        """Process one batch and apply its projected outcome to executor state."""
        output = await self._batch_processing_service.process_batch(
            records=records,
            start_index=start_index,
            query_string=query_string,
        )
        apply_processed_batch_outcome(
            state=state,
            outcome=build_processed_batch_outcome(
                records=records,
                output=output,
            ),
        )

    def build_batch_result(
        self,
        *,
        state: _BatchExecutionStatisticsState,
        batch_result_type: _BatchResultBuilder[_BatchResultT],
    ) -> _BatchResultT:
        """Project current cumulative counters into public batch result."""
        return batch_result_type(
            bronze_count=state.records_bronze,
            silver_count=state.records_silver,
            gold_count=state.records_gold,
            quarantined_count=state.records_quarantined,
        )

    def build_run_statistics(
        self,
        *,
        state: _BatchExecutionStatisticsState,
    ) -> dict[str, int | list[str]]:
        """Project deterministic run statistics from current executor state."""
        return build_run_statistics(
            records_fetched=state.records_fetched,
            records_bronze=state.records_bronze,
            records_silver=state.records_silver,
            records_gold=state.records_gold,
            records_quarantined=state.records_quarantined,
            records_filtered_out=state.records_filtered_out,
            source_batch_ids=state._source_batch_ids,
        )
