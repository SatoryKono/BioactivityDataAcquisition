"""Stable data transfer objects for batch processing outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@dataclass(frozen=True, slots=True)
class BatchProcessingOutcome:
    """Executor-facing immutable result of one successfully processed batch."""
    batch_id: BatchID
    bronze_result: BronzeWriteResult | None
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int
    gold_excluded_by_contract_count: int = 0
