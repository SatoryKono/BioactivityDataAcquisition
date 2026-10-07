"""Stable data transfer objects for batch processing outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

WriteLayerStatus = Literal["written", "quarantined", "blocked", "skipped"]
"""Disposition of one storage-layer write attempt.

- ``written``: the writer port call completed; ``confirmed_count`` candidate
  records were accepted by the layer.
- ``quarantined``: a schema violation was raised and all candidates were
  persisted to quarantine; nothing was confirmed written.
- ``blocked``: the layer was not invoked because an upstream layer outcome
  forbade it (e.g. Gold after a Silver quarantine).
- ``skipped``: the layer had no candidates and was not invoked.
"""


@dataclass(frozen=True, slots=True)
class LayerWriteOutcome:
    """Typed result of one storage-layer write attempt.

    ``candidate_count`` counts layer-derived rows offered to the writer;
    ``confirmed_count`` counts rows the writer port accepted;
    ``quarantined_count`` counts rows persisted to quarantine at this stage.
    """

    layer: str
    status: WriteLayerStatus
    candidate_count: int
    confirmed_count: int = 0
    quarantined_count: int = 0
    write_result: object | None = None


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
