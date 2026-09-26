"""Internal system-level exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType

__all__ = ["MetricsServerError", "RunnerAlreadyExecutedError"]


class MetricsServerError(CriticalError):
    """Raised when metrics server fails to start with fail_fast=True."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        port: int,
        reason: str,
        original_error: Exception | None = None,
    ) -> None:
        self.port = port
        self.reason = reason
        self.original_error = original_error
        super().__init__(f"Failed to start metrics server on port {port}: {reason}")


class RunnerAlreadyExecutedError(CriticalError):
    """Raised when attempting to run a pipeline runner that has already executed."""

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        runner_type: str,
        run_id: str,
        final_state: str | None = None,
    ) -> None:
        self.runner_type = runner_type
        self.run_id = run_id
        self.final_state = final_state
        msg = f"{runner_type} already executed (run_id={run_id})"
        if final_state:
            msg += f", final_state={final_state}"
        msg += ". Create a new Runner instance for another run."
        super().__init__(msg)
