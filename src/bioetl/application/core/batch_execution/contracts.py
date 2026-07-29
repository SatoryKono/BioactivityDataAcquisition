"""Shared internal contracts for batch-execution orchestration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord, JsonDict

_BatchResultT = TypeVar("_BatchResultT", covariant=True)


class BatchExecutionCountersSnapshot(Protocol):
    """Shared counter snapshot required by batch-execution finalization flows."""
    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_gold_excluded_by_contract: int
    records_quarantined: int


class BatchExecutionStatisticsState(BatchExecutionCountersSnapshot, Protocol):
    """Extended statistics snapshot used for public batch/run projections."""
    records_filtered_out: int
    _source_batch_ids: list[str]


class BatchExecutionMemoryState(Protocol):
    """Memory sizing statistics used during execution finalization."""
    batch_size_reductions: int
    min_batch_size_used: int
    def decision_trace_dicts(self) -> tuple[JsonDict, ...]:
        """Return immutable decision-trace payloads for batch sizing."""
        ...


class BatchResultBuilderProtocol(Protocol[_BatchResultT]):
    """Callable result factory used to project cumulative batch counters."""
    def __call__(
        self,
        *,
        bronze_count: int,
        silver_count: int,
        gold_count: int,
        quarantined_count: int,
    ) -> _BatchResultT: ...


class BatchExecutionStateProtocol(BatchExecutionStatisticsState, Protocol):
    """Mutable executor state required to apply processed-batch outcomes."""
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
