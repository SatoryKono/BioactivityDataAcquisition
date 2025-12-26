"""Critical exceptions that stop pipeline execution.

These errors indicate serious problems that cannot be recovered from
and require immediate attention.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType


class LockLostError(CriticalError):
    """Raised when distributed lock is lost during execution.

    This is a CRITICAL error - worker MUST terminate before any commit.
    Losing the lock means another worker may have acquired it.
    """

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, run_id: str | None = None) -> None:
        self.key = key
        self.run_id = run_id
        msg = f"Lock lost: {key}"
        if run_id:
            msg += f" (run_id={run_id})"
        super().__init__(msg)


class LockAcquisitionError(CriticalError):
    """Raised when lock cannot be acquired.

    This prevents the pipeline from starting if the lock is held by another worker.
    """

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, current_owner: str | None = None) -> None:
        self.key = key
        self.current_owner = current_owner
        msg = f"Failed to acquire lock: {key}"
        if current_owner:
            msg += f" (owned by {current_owner})"
        super().__init__(msg)


class CheckpointConflictError(CriticalError):
    """Raised when checkpoint write fails due to concurrent modification.

    This indicates that another worker has modified the checkpoint,
    which could lead to data inconsistency.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, pipeline: str, message: str) -> None:
        self.pipeline = pipeline
        super().__init__(f"Checkpoint conflict in '{pipeline}': {message}")


class MergeConflictError(CriticalError):
    """Raised when Delta merge has conflicts.

    This indicates that the data merge operation has unresolved conflicts
    that require manual intervention.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table: str, conflicts: int) -> None:
        self.table = table
        self.conflicts = conflicts
        super().__init__(f"Merge conflict in '{table}': {conflicts} conflicts")


class AuthFailureError(CriticalError):
    """Raised when API authentication fails (401, 403).

    This is a CRITICAL error - pipeline should not continue without valid auth.
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(self, provider: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        msg = f"Authentication failed for {provider}"
        if status_code:
            msg += f" (HTTP {status_code})"
        super().__init__(msg)


class InfrastructureError(CriticalError):
    """Raised when infrastructure health check fails.

    This is a CRITICAL error - pipeline should not start if infrastructure
    is unavailable (storage or data source unreachable).
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, message: str, failed_components: list[str] | None = None) -> None:
        self.failed_components = failed_components or []
        super().__init__(message)


class PolicyViolationError(CriticalError):
    """Raised when medallion layer policy is violated.

    This is a CRITICAL error - pipeline must not proceed with invalid
    write mode for a given medallion layer.

    Example:
        - Bronze layer only allows APPEND mode
        - Attempting OVERWRITE on Bronze raises PolicyViolationError
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(self, message: str) -> None:
        super().__init__(message)
