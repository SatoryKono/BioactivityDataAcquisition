"""Internal logic exceptions.

These errors indicate that the system is in an incorrect or unexpected state.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType


class InternalError(BioETLError):
    """Base class for internal logic errors or invariant violations within the application."""

    error_type = ErrorType.INVALID_DATA


class PolicyViolationError(InternalError):
    """Raised when a defined business or pipeline policy is violated."""

    error_type = ErrorType.INVALID_DATA

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidStateError(InternalError):
    """Raised when an operation is attempted in an invalid state."""

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


class AuthFailureError(InternalError):
    """Raised when the application fails to authenticate to a required service in a non-recoverable way.

    This forces pipeline termination.
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(self, provider: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        msg = f"Authentication failed for {provider}"
        if status_code:
            msg += f" (HTTP {status_code})"
        super().__init__(msg)
