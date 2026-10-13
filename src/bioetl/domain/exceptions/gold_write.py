"""Gold outcome errors preserve their immutable receipt and original cause."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from bioetl.domain.types.gold_contracts import GoldWriteReceipt


class GoldWriteFailure(BioETLError):
    """A failed operation with an independently classified commit outcome."""

    error_type = ErrorType.DB_UNAVAILABLE
    reason_code = "gold_write_outcome_requires_reconciliation"

    def __init__(
        self,
        receipt: GoldWriteReceipt,
        *,
        diagnostic_error: BaseException | None = None,
    ) -> None:
        self.receipt = receipt
        self.diagnostic_error = diagnostic_error
        super().__init__(f"Gold write {receipt.physical_table}: {receipt.category}")


class GoldWriteValidationFailure(GoldWriteFailure, ValueError):
    """A rejected precommit request; preserve its validation classification."""

    error_type = ErrorType.INVALID_DATA
    reason_code = "gold_write_validation_failed"

    def __init__(
        self,
        receipt: GoldWriteReceipt,
        original: ValueError,
        *,
        diagnostic_error: BaseException | None = None,
    ) -> None:
        from bioetl.domain.error_classifier import ErrorClassifier

        super().__init__(receipt, diagnostic_error=diagnostic_error)
        self.error_type_override = ErrorClassifier().classify(original)
        self.args = (str(original),)


class GoldWriteCancelled(Exception):
    """Framework-neutral cancellation intent translated by the async adapter."""

    def __init__(self, receipt: GoldWriteReceipt) -> None:
        self.receipt = receipt
        Exception.__init__(
            self, f"Gold write cancelled: {receipt.physical_table}: {receipt.category}"
        )
