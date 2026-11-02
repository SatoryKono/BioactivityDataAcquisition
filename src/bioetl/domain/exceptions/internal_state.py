"""Internal state/invariant exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType

__all__ = ["InvalidStateError", "PolicyViolationError"]


class InvalidStateError(CriticalError):
    """Raised when an aggregate operation is attempted in an invalid state."""

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        current_state: str | None = None,
        attempted_operation: str | None = None,
    ) -> None:
        self.current_state = current_state
        self.attempted_operation = attempted_operation
        super().__init__(message)


class PolicyViolationError(CriticalError):
    """Raised when medallion layer policy is violated."""

    error_type = ErrorType.INVALID_DATA

    def __init__(self, message: str) -> None:
        super().__init__(message)
