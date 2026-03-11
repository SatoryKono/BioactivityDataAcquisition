"""Internal helper functions for batch execution state updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.batch_processing_service import BatchProcessingOutput


__all__ = [
    "BatchExecutionStateOutcome",
    "build_batch_execution_state_update",
    "build_run_statistics",
]


@dataclass(frozen=True, slots=True)
class BatchExecutionStateOutcome:
    """Counter deltas and metadata produced by one processed batch."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int
    filtered_out_count: int
    source_batch_id: str


def build_batch_execution_state_update(
    *,
    input_record_count: int,
    output: BatchProcessingOutput,
) -> BatchExecutionStateOutcome:
    """Project batch-processing output into executor-level state deltas."""
    return BatchExecutionStateOutcome(
        bronze_count=input_record_count,
        silver_count=len(output.silver_records),
        gold_count=len(output.gold_records),
        quarantined_count=output.quarantined_count,
        filtered_out_count=output.filtered_out_count,
        source_batch_id=str(output.batch_id),
    )


def build_run_statistics(
    *,
    records_fetched: int,
    records_bronze: int,
    records_silver: int,
    records_gold: int,
    records_quarantined: int,
    records_filtered_out: int,
    source_batch_ids: list[str],
) -> dict[str, int | list[str]]:
    """Build deterministic run statistics from executor-level counters."""
    return {
        "records_fetched": records_fetched,
        "records_bronze": records_bronze,
        "records_silver": records_silver,
        "records_gold": records_gold,
        "records_quarantined": records_quarantined,
        "records_filtered_out": records_filtered_out,
        "source_batch_ids": list(dict.fromkeys(source_batch_ids)),
    }
