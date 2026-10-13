"""Gold outcome errors preserve their immutable receipt and original cause."""

from __future__ import annotations

from asyncio import CancelledError
from typing import TYPE_CHECKING

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from bioetl.domain.types.gold_contracts import GoldWriteReceipt


class GoldWriteFailure(BioETLError):
    """A failed operation with an independently classified commit outcome."""

    error_type = ErrorType.DB_UNAVAILABLE
    reason_code = "gold_write_outcome_requires_reconciliation"

    def __init__(self, receipt: GoldWriteReceipt) -> None:
        self.receipt = receipt
        super().__init__(f"Gold write {receipt.physical_table}: {receipt.category}")


class GoldWriteCancelled(CancelledError):
    """Cancellation remains cancellation, even when a commit is already proven."""

    def __init__(self, receipt: GoldWriteReceipt) -> None:
        self.receipt = receipt
        super().__init__(
            f"Gold write cancelled: {receipt.physical_table}: {receipt.category}"
        )
