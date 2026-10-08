"""Stable data transfer objects for batch processing outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.batch_processing_contracts import (
    LayerWriteOutcome,
)
from bioetl.application.batch_processing_contracts import (
    WriteLayerStatus as WriteLayerStatus,
)
from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@dataclass(frozen=True, slots=True)
class SilverGoldWriteOutcome:
    """Confirmed write outcomes for the Silver-then-Gold choreography."""

    silver: LayerWriteOutcome
    gold: LayerWriteOutcome


@dataclass(frozen=True, slots=True)
class BatchProcessingOutcome:
    """Executor-facing immutable result of one successfully processed batch.

    ``silver_records``/``gold_records`` are transform-stage candidates.
    Confirmed persistence must be read from ``silver_write``/``gold_write``.
    """

    batch_id: BatchID
    bronze_result: BronzeWriteResult | None
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int
    silver_write: LayerWriteOutcome
    gold_write: LayerWriteOutcome
    gold_excluded_by_contract_count: int = 0

    @property
    def confirmed_silver_records(self) -> list[BronzeRecord]:
        """Silver candidate rows confirmed written to storage."""
        if self.silver_write.status == "written":
            return self.silver_records
        return []

    @property
    def confirmed_gold_records(self) -> list[GoldRecord]:
        """Gold candidate rows confirmed written to storage."""
        if self.gold_write.status == "written":
            return self.gold_records
        return []

    @property
    def write_quarantined_count(self) -> int:
        """Records quarantined at the storage-write stage (Silver + Gold)."""
        return self.silver_write.quarantined_count + self.gold_write.quarantined_count

    @property
    def total_quarantined_count(self) -> int:
        """Records quarantined across transform and write stages."""
        return self.quarantined_count + self.write_quarantined_count

    @property
    def silver_quarantined_count(self) -> int:
        """Rejections on the Silver path (transform + Silver write stage)."""
        return self.quarantined_count + self.silver_write.quarantined_count

    @property
    def gold_quarantined_count(self) -> int:
        """Rejections at the Gold write stage."""
        return self.gold_write.quarantined_count
