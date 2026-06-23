"""Pipeline shutdown exception and shutdown reason enumeration.

These types are defined in the domain layer so they can be referenced
by any layer without creating circular dependencies.

Both application.core.shutdown and application.services.shutdown_service
previously defined these inline, causing a soft circular import:
  shutdown.py -> shutdown_service.py (re-export)
  pipeline_run_execution_service.py -> shutdown.py (lazy, runtime-only)

Moving them here breaks that cycle: all layers import from domain.exceptions.
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType

__all__ = ["PipelineShutdownError", "ShutdownReason"]


class ShutdownReason(Enum):
    """Enumeration of shutdown reasons for metrics and logging."""

    SIGNAL_SIGTERM = "SIGTERM"
    SIGNAL_SIGINT = "SIGINT"
    LOCK_LOST = "lock_lost"
    DQ_THRESHOLD_EXCEEDED = "dq_threshold"
    TIMEOUT = "timeout"
    USER_REQUESTED = "user_requested"
    UNKNOWN = "unknown"


class PipelineShutdownError(CriticalError):
    """Raised when pipeline receives shutdown signal.

    This exception signals that the pipeline should gracefully terminate,
    saving any pending checkpoints before exit.

    Attributes:
        reason: The reason for shutdown.
    """

    error_type: ClassVar[ErrorType] = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        message: str = "Pipeline shutdown requested",
        *,
        reason: ShutdownReason | None = None,
    ) -> None:
        """Initialize PipelineShutdownError.

        Args:
            message: Error message describing the shutdown cause.
            reason: Optional ShutdownReason enum value.
        """
        super().__init__(message)
        self.reason = reason or ShutdownReason.UNKNOWN
