"""Shared application-level contracts for batch writes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["LayerWriteOutcome", "WriteLayerStatus"]

WriteLayerStatus = Literal["written", "quarantined", "blocked", "skipped"]
"""Disposition of one storage-layer write attempt."""


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
