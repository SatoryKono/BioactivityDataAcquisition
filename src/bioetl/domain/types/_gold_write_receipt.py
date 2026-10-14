"""Domain types for Gold layer write outcomes and receipts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["GoldWriteCategory", "GoldWriteReceipt"]


class GoldWriteCategory(StrEnum):
    """Categorization of physical commit and postwrite status."""

    NOT_COMMITTED = "NOT_COMMITTED"
    """No physical commit was started, or noncommit was established."""

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
    committed_targets: tuple[str, ...] = ()


def require_complete_gold_receipt(value: object) -> GoldWriteReceipt:
    """Confirm a completed Gold operation, retaining any incomplete commit proof."""
    from bioetl.domain.exceptions.gold_write import GoldWriteFailure

    if not isinstance(value, GoldWriteReceipt):
        raise TypeError("Gold storage must return a GoldWriteReceipt")
    if value.category != GoldWriteCategory.COMPLETE:
        raise GoldWriteFailure(value)
    return value
