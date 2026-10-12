"""Internal helper functions for batch execution state updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.batch_execution.contracts import (
    BatchExecutionStateProtocol,
    BatchResultBuilderProtocol,
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
    """Counter deltas and metadata produced by one processed batch.

    ``silver_count``/``gold_count`` are confirmed persistence counts.
    ``quarantined_count`` is the batch total across transform and write
    stages; ``silver_quarantined_count``/``gold_quarantined_count`` carry the
    per-layer write rejections for per-layer DQ accounting.
    """

    bronze_count: int
    silver_count: int
    gold_count: int
    gold_excluded_by_contract_count: int
    quarantined_count: int
    filtered_out_count: int
    source_batch_id: str
    silver_quarantined_count: int = 0
    gold_quarantined_count: int = 0


@dataclass(frozen=True, slots=True)
class BatchProcessedOutcome:
    """One processed batch projected into state-update and DQ payloads.

    ``confirmed_silver_records``/``confirmed_gold_records`` contain only the
    rows the storage layer actually persisted (empty when the layer was
    quarantined, blocked, or skipped).
    """

    records: list[BronzeRecord]
    state_update: BatchExecutionStateOutcome
    batch_id: BatchID
    bronze_result: object
    confirmed_silver_records: list[BronzeRecord]
    confirmed_gold_records: list[GoldRecord]


def build_batch_execution_state_update(
    *,
    input_record_count: int,
    output: BatchProcessingOutcome,
) -> BatchExecutionStateOutcome:
    """Project batch-processing output into executor-level state deltas."""
    return BatchExecutionStateOutcome(
        bronze_count=input_record_count,
        silver_count=output.silver_write.confirmed_count,
        gold_count=output.gold_write.confirmed_count,
        gold_excluded_by_contract_count=output.gold_excluded_by_contract_count,
        quarantined_count=output.total_quarantined_count,
        filtered_out_count=output.filtered_out_count,
        source_batch_id=str(output.batch_id),
        silver_quarantined_count=output.silver_quarantined_count,
        gold_quarantined_count=output.gold_quarantined_count,
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
        confirmed_silver_records=output.confirmed_silver_records,
        confirmed_gold_records=output.confirmed_gold_records,
    )


def apply_batch_execution_state_update(
    *,
    state: BatchExecutionStateProtocol,
    state_update: BatchExecutionStateOutcome,
) -> None:
    """Apply one batch of counter deltas to executor-level state."""
    state.records_bronze += state_update.bronze_count
    state.records_silver += state_update.silver_count
    state.records_gold += state_update.gold_count
    state.records_gold_excluded_by_contract += (
        state_update.gold_excluded_by_contract_count
    )
    state.records_quarantined += state_update.quarantined_count
    state.records_quarantined_silver += state_update.silver_quarantined_count
    state.records_quarantined_gold += state_update.gold_quarantined_count
    state.records_filtered_out += state_update.filtered_out_count
    state.source_batch_ids.append(state_update.source_batch_id)


def apply_processed_batch_outcome(
    *,
    state: BatchExecutionStateProtocol,
    outcome: BatchProcessedOutcome,
) -> None:
    """Apply one processed-batch outcome to executor counters and DQ buffers."""
    apply_batch_execution_state_update(
        state=state,
        state_update=outcome.state_update,
    )
    if not state.should_collect_dq_data():
        return
    state.collect_dq_data(
        records=outcome.records,
        batch_id=outcome.batch_id,
        bronze_result=outcome.bronze_result,
        silver_records=outcome.confirmed_silver_records,
        gold_records=outcome.confirmed_gold_records,
    )


def build_batch_result_snapshot[BatchResultT](
    *,
    batch_result_type: BatchResultBuilderProtocol[BatchResultT],
    records_bronze: int,
    records_silver: int,
    records_gold: int,
    records_quarantined: int,
) -> BatchResultT:
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
    records_gold_excluded_by_contract: int,
    records_quarantined: int,
    records_filtered_out: int,
    source_batch_ids: list[str],
    records_quarantined_silver: int = 0,
    records_quarantined_gold: int = 0,
) -> dict[str, int | list[str]]:
    """Build deterministic run statistics from executor-level counters."""
    return {
        "records_fetched": records_fetched,
        "records_bronze": records_bronze,
        "records_silver": records_silver,
        "records_gold": records_gold,
        "records_gold_excluded_by_contract": records_gold_excluded_by_contract,
        "records_quarantined": records_quarantined,
        "records_quarantined_silver": records_quarantined_silver,
        "records_quarantined_gold": records_quarantined_gold,
        "records_filtered_out": records_filtered_out,
        "source_batch_ids": list(dict.fromkeys(source_batch_ids)),
    }
