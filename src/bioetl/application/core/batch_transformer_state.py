"""State and result helpers for batch transformation."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
)
from bioetl.domain.types import BronzeRecord, GoldRecord

__all__ = [
    "RecordTransformOutcome",
    "TransformAggregationState",
    "TransformResult",
    "TransformedRecord",
    "accumulate_stream_transform_result",
    "accumulate_transform_outcome",
    "apply_stream_transform_result_to_state",
    "apply_transform_outcome_to_state",
    "build_transform_result",
    "create_transform_aggregation_state",
]

@dataclass(frozen=True, slots=True)
class RecordTransformOutcome:
    """Internal outcome of transforming one record before quarantine flush."""
    silver_record: BronzeRecord | None
    gold_record: GoldRecord | None
    gold_excluded_by_contract: bool = False
    filtered_entry: FilteredQuarantineEntry | None = None
    dq_entry: DQQuarantineEntry | None = None

@dataclass(frozen=True, slots=True)
class TransformResult:
    """Result of batch transformation."""
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    gold_excluded_by_contract_count: int = 0
    filtered_out_count: int = 0
    records_quarantine_failed: int = 0

@dataclass(frozen=True, slots=True)
class TransformedRecord:
    """Single transformed record with routing info."""
    silver_record: BronzeRecord | None
    gold_record: GoldRecord | None
    is_quarantined: bool
    gold_excluded_by_contract: bool = False
    is_filtered_out: bool = False
    quarantine_write_failed: bool = False

@dataclass(slots=True)
class TransformAggregationState:
    """Mutable aggregation state shared by batch and streaming transforms."""
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    filtered_records: list[FilteredQuarantineEntry] = field(default_factory=list)
    dq_records: list[DQQuarantineEntry] = field(default_factory=list)
    quarantined_count: int = 0
    gold_excluded_by_contract_count: int = 0
    filtered_out_count: int = 0
    records_quarantine_failed: int = 0

def create_transform_aggregation_state() -> TransformAggregationState:
    """Create empty aggregation state for one transform run."""
    return TransformAggregationState(
        silver_records=[],
        gold_records=[],
    )

def accumulate_transform_outcome(
    *,
    attempt: RecordTransformOutcome,
    silver_records: list[BronzeRecord],
    gold_records: list[GoldRecord],
    filtered_records: list[FilteredQuarantineEntry],
    dq_records: list[DQQuarantineEntry],
) -> tuple[int, int]:
    """Route a transformed-record outcome into batch accumulators."""
    if attempt.filtered_entry is not None:
        filtered_records.append(attempt.filtered_entry)
        return 0, 1
    if attempt.dq_entry is not None:
        dq_records.append(attempt.dq_entry)
        return 1, 0
    if attempt.silver_record is not None:
        silver_records.append(attempt.silver_record)
        if attempt.gold_record is not None:
            gold_records.append(attempt.gold_record)
    return 0, 0

def apply_transform_outcome_to_state(
    *,
    state: TransformAggregationState,
    attempt: RecordTransformOutcome,
) -> None:
    """Apply one batch transform outcome to aggregate state."""
    quarantined_delta, filtered_delta = accumulate_transform_outcome(
        attempt=attempt,
        silver_records=state.silver_records,
        gold_records=state.gold_records,
        filtered_records=state.filtered_records,
        dq_records=state.dq_records,
    )
    state.quarantined_count += quarantined_delta
    state.filtered_out_count += filtered_delta
    if (
        attempt.silver_record is not None
        and attempt.gold_record is None
        and attempt.gold_excluded_by_contract
    ):
        state.gold_excluded_by_contract_count += 1

def accumulate_stream_transform_result(
    *,
    result: TransformedRecord,
    silver_records: list[BronzeRecord],
    gold_records: list[GoldRecord],
) -> tuple[int, int, int]:
    """Route a single streaming transform result into accumulators."""
    quarantine_failed_delta = int(result.quarantine_write_failed)
    if result.is_quarantined:
        return 1, 0, quarantine_failed_delta
    if result.is_filtered_out:
        return 0, 1, quarantine_failed_delta
    if result.silver_record is not None:
        silver_records.append(result.silver_record)
        if result.gold_record is not None:
            gold_records.append(result.gold_record)
    return 0, 0, quarantine_failed_delta

def apply_stream_transform_result_to_state(
    *,
    state: TransformAggregationState,
    result: TransformedRecord,
) -> None:
    """Apply one streaming transform result to aggregate state."""
    quarantined_delta, filtered_delta, failed_delta = (
        accumulate_stream_transform_result(
            result=result,
            silver_records=state.silver_records,
            gold_records=state.gold_records,
        )
    )
    state.quarantined_count += quarantined_delta
    state.filtered_out_count += filtered_delta
    state.records_quarantine_failed += failed_delta
    if (
        result.silver_record is not None
        and result.gold_record is None
        and result.gold_excluded_by_contract
    ):
        state.gold_excluded_by_contract_count += 1

def build_transform_result(state: TransformAggregationState) -> TransformResult:
    """Build public transform result from aggregate state."""
    return TransformResult(
        silver_records=state.silver_records,
        gold_records=state.gold_records,
        quarantined_count=state.quarantined_count,
        gold_excluded_by_contract_count=state.gold_excluded_by_contract_count,
        filtered_out_count=state.filtered_out_count,
        records_quarantine_failed=state.records_quarantine_failed,
    )
