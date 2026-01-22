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

    def __init__(
        self, message: str, failed_components: list[str] | None = None
    ) -> None:
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


class InvalidStateError(CriticalError):
    """Raised when an aggregate operation is attempted in an invalid state.

    This is a CRITICAL error indicating an invariant violation attempt.
    Aggregates use this to enforce state machine transitions and business rules.

    Example:
        - Attempting to complete a PipelineRun that has failed stages
        - Attempting to record stages on an already completed run
        - Mutating a Batch after it has been sealed
    """

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


class MetricsServerError(CriticalError):
    """Raised when metrics server fails to start with fail_fast=True.

    This is a CRITICAL error - if fail_fast is enabled, the pipeline
    should not start without operational metrics collection.

    This exception is raised by the Prometheus metrics server when it cannot
    bind to the specified port and fail_fast mode is enabled.

    Attributes:
        port: Port that failed to bind.
        reason: Reason for failure (e.g., "port_in_use", "os_error", "unexpected").
        original_error: Underlying exception that caused the failure.
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self, port: int, reason: str, original_error: Exception | None = None
    ) -> None:
        """Initialize MetricsServerError.

        Args:
            port: Port that failed.
            reason: Reason for failure.
            original_error: Underlying exception.
        """
        self.port = port
        self.reason = reason
        self.original_error = original_error
        super().__init__(f"Failed to start metrics server on port {port}: {reason}")


class RunnerAlreadyExecutedError(CriticalError):
    """Raised when attempting to run a pipeline runner that has already executed.

    This is a CRITICAL error - each Runner instance should only be executed once.
    Create a new Runner instance for another run.

    This prevents undefined behavior from reusing Runner instances that have
    internal state from previous executions (checkpoints, metrics, timestamps).

    Attributes:
        runner_type: Type of runner (e.g., "CompositePipelineRunner").
        run_id: The run ID of the already-executed run.
        final_state: The final state of the previous execution (if available).
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        runner_type: str,
        run_id: str,
        final_state: str | None = None,
    ) -> None:
        """Initialize RunnerAlreadyExecutedError.

        Args:
            runner_type: Type of runner.
            run_id: Run ID of the executed run.
            final_state: Final state of the previous execution.
        """
        self.runner_type = runner_type
        self.run_id = run_id
        self.final_state = final_state
        msg = f"{runner_type} already executed (run_id={run_id})"
        if final_state:
            msg += f", final_state={final_state}"
        msg += ". Create a new Runner instance for another run."
        super().__init__(msg)
