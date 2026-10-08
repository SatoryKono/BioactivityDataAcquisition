"""Domain types for Gold layer write outcomes and receipts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["GoldWriteCategory", "GoldWriteReceipt"]


class GoldWriteCategory(StrEnum):
    """Categorization of physical commit and postwrite status."""

    NOT_COMMITTED = "NOT_COMMITTED"
    """Write failed before or during physical commit. Target is unchanged."""

    COMMITTED_POSTWRITE_PENDING = "COMMITTED_POSTWRITE_PENDING"
    """Physical commit succeeded, but postwrite side effects (metadata/lineage) failed."""

    COMPLETE = "COMPLETE"
    """Physical commit and all postwrite side effects succeeded."""

    UNKNOWN = "UNKNOWN"
    """Ambiguous outcome (e.g. timeout or cancellation). Requires inspection."""


@dataclass(frozen=True, slots=True)
class GoldWriteReceipt:
    """Receipt proving the outcome category of a Gold write attempt."""

    physical_table: str
    contract_version: str
    category: GoldWriteCategory
