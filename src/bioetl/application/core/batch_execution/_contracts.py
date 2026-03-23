"""Shared internal contracts for batch-execution orchestration helpers."""

from __future__ import annotations

from typing import Protocol


class BatchExecutionCountersSnapshot(Protocol):
    """Shared counter snapshot required by batch-execution finalization flows."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


class BatchExecutionStatisticsState(BatchExecutionCountersSnapshot, Protocol):
    """Extended statistics snapshot used for public batch/run projections."""

    records_filtered_out: int
    _source_batch_ids: list[str]


class BatchExecutionMemoryState(Protocol):
    """Memory sizing statistics used during execution finalization."""

    batch_size_reductions: int
    min_batch_size_used: int
