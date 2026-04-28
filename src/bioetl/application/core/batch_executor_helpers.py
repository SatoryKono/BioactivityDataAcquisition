# ruff: noqa: UP049
"""Internal helper functions for batch execution state updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_execution.contracts import (
    BatchExecutionStatePort,
    BatchResultBuilderPort,
)

if TYPE_CHECKING:
    from bioetl.application.core.batch_processing_contracts import (
        BatchProcessingOutcome,
    )
    from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord


__all__ = [
    "BatchExecutionStateOutcome",
    "BatchProcessedOutcome",
    "apply_batch_execution_state_update",
    "apply_processed_batch_outcome",
    "build_batch_execution_state_update",
    "build_batch_result_snapshot",
    "build_processed_batch_outcome",
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


@dataclass(frozen=True, slots=True)
class BatchProcessedOutcome:
    """One processed batch projected into state-update and DQ payloads."""

    records: list[BronzeRecord]
    state_update: BatchExecutionStateOutcome
    batch_id: BatchID
    bronze_result: object
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]


def build_batch_execution_state_update(
    *,
    input_record_count: int,
    output: BatchProcessingOutcome,
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


def build_processed_batch_outcome(
    *,
    records: list[BronzeRecord],
    output: BatchProcessingOutcome,
) -> BatchProcessedOutcome:
    """Project one processed batch into explicit state and DQ outcome payloads."""
    return BatchProcessedOutcome(
        records=records,
        state_update=build_batch_execution_state_update(
            input_record_count=len(records),
            output=output,
        ),
        batch_id=output.batch_id,
        bronze_result=output.bronze_result,
        silver_records=output.silver_records,
        gold_records=output.gold_records,
    )


def apply_batch_execution_state_update(
    *,
    state: BatchExecutionStatePort,
    state_update: BatchExecutionStateOutcome,
) -> None:
    """Apply one batch of counter deltas to executor-level state."""
    state.records_bronze += state_update.bronze_count
    state.records_silver += state_update.silver_count
    state.records_gold += state_update.gold_count
    state.records_quarantined += state_update.quarantined_count
    state.records_filtered_out += state_update.filtered_out_count
    state._source_batch_ids.append(state_update.source_batch_id)


def apply_processed_batch_outcome(
    *,
    state: BatchExecutionStatePort,
    outcome: BatchProcessedOutcome,
) -> None:
    """Apply one processed-batch outcome to executor counters and DQ buffers."""
    apply_batch_execution_state_update(
        state=state,
        state_update=outcome.state_update,
    )
    if not state._should_collect_dq_data():
        return
    state._collect_dq_data(
        records=outcome.records,
        batch_id=outcome.batch_id,
        bronze_result=outcome.bronze_result,
        silver_records=outcome.silver_records,
        gold_records=outcome.gold_records,
    )


def build_batch_result_snapshot[_BatchResultT](
    *,
    batch_result_type: BatchResultBuilderPort[_BatchResultT],
    records_bronze: int,
    records_silver: int,
    records_gold: int,
    records_quarantined: int,
) -> _BatchResultT:
    """Build the public batch-result snapshot from cumulative executor counters."""
    return batch_result_type(
        bronze_count=records_bronze,
        silver_count=records_silver,
        gold_count=records_gold,
        quarantined_count=records_quarantined,
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
