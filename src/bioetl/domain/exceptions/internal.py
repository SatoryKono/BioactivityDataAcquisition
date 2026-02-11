"""Internal exceptions for critical application errors.

These errors indicate serious problems that cannot be recovered from and require
immediate attention. They typically result in pipeline termination.

Категория: InternalErrors - внутренние ошибки приложения (непредвиденные сбои,
некорректное состояние, нарушение внутренних инвариантов, сбои fallback-логики),
как правило критические и требующие немедленной остановки процесса ETL.

All exceptions in this module inherit from CriticalError, indicating that
the pipeline should stop immediately.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.types import ErrorType

# =============================================================================
# Base Internal Exception
# =============================================================================


# =============================================================================
# State and Invariant Violations
# =============================================================================


class InvalidStateError(CriticalError):
    """Raised when an aggregate operation is attempted in an invalid state.

    This is a CRITICAL error indicating an invariant violation attempt.
    Aggregates use this to enforce state machine transitions and business rules.

    Examples:
        - Attempting to complete a PipelineRun that has failed stages
        - Attempting to record stages on an already completed run
        - Mutating a Batch after it has been sealed

    Attributes:
        current_state: Optional current state of the object.
        attempted_operation: Optional description of the attempted operation.

    Example:
        >>> raise InvalidStateError(
        ...     "Cannot complete run with failed stages",
        ...     current_state="FAILED",
        ...     attempted_operation="complete"
        ... )
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        current_state: str | None = None,
        attempted_operation: str | None = None,
    ) -> None:
        """Initialize InvalidStateError.

        Args:
            message: Description of the state violation.
            current_state: Optional current state of the object.
            attempted_operation: Optional description of the attempted operation.
        """
        self.current_state = current_state
        self.attempted_operation = attempted_operation
        super().__init__(message)


class PolicyViolationError(CriticalError):
    """Raised when medallion layer policy is violated.

    This is a CRITICAL error - pipeline must not proceed with invalid
    write mode for a given medallion layer.

    Examples:
        - Bronze layer only allows APPEND mode
        - Attempting OVERWRITE on Bronze raises PolicyViolationError

    Example:
        >>> raise PolicyViolationError(
        ...     "Bronze layer does not support OVERWRITE mode"
        ... )
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(self, message: str) -> None:
        """Initialize PolicyViolationError.

        Args:
            message: Description of the policy violation.
        """
        super().__init__(message)


# =============================================================================
# Lock Errors
# =============================================================================


class LockLostError(CriticalError):
    """Raised when distributed lock is lost during execution.

    This is a CRITICAL error - worker MUST terminate before any commit.
    Losing the lock means another worker may have acquired it.

    Attributes:
        key: Lock key that was lost.
        run_id: Optional run ID of the affected pipeline run.

    Example:
        >>> raise LockLostError("lock:chembl_activity", run_id="run-123")
    """

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, run_id: str | None = None) -> None:
        """Initialize LockLostError.

        Args:
            key: Lock key that was lost.
            run_id: Optional run ID of the affected pipeline run.
        """
        self.key = key
        self.run_id = run_id
        msg = f"Lock lost: {key}"
        if run_id:
            msg += f" (run_id={run_id})"
        super().__init__(msg)


class LockAcquisitionError(CriticalError):
    """Raised when lock cannot be acquired.

    This prevents the pipeline from starting if the lock is held by another worker.

    Attributes:
        key: Lock key that could not be acquired.
        current_owner: Optional identifier of the current lock owner.

    Example:
        >>> raise LockAcquisitionError("lock:chembl_activity", current_owner="worker-456")
    """

    error_type = ErrorType.LOCK_LOST

    def __init__(self, key: str, current_owner: str | None = None) -> None:
        """Initialize LockAcquisitionError.

        Args:
            key: Lock key that could not be acquired.
            current_owner: Optional identifier of the current lock owner.
        """
        self.key = key
        self.current_owner = current_owner
        msg = f"Failed to acquire lock: {key}"
        if current_owner:
            msg += f" (owned by {current_owner})"
        super().__init__(msg)


# =============================================================================
# Data Integrity Errors
# =============================================================================


class CheckpointConflictError(CriticalError):
    """Raised when checkpoint write fails due to concurrent modification.

    This indicates that another worker has modified the checkpoint,
    which could lead to data inconsistency.

    Attributes:
        pipeline: Name of the pipeline with checkpoint conflict.

    Example:
        >>> raise CheckpointConflictError(
        ...     "chembl_activity",
        ...     "Version mismatch: expected 5, found 6"
        ... )
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, pipeline: str, message: str) -> None:
        """Initialize CheckpointConflictError.

        Args:
            pipeline: Name of the pipeline with checkpoint conflict.
            message: Description of the conflict.
        """
        self.pipeline = pipeline
        super().__init__(f"Checkpoint conflict in '{pipeline}': {message}")


class MergeConflictError(CriticalError):
    """Raised when Delta merge has conflicts.

    This indicates that the data merge operation has unresolved conflicts
    that require manual intervention.

    Attributes:
        table: Name of the table with merge conflicts.
        conflicts: Number of conflicting records.

    Example:
        >>> raise MergeConflictError("chembl_activity", conflicts=42)
    """

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(self, table: str, conflicts: int) -> None:
        """Initialize MergeConflictError.

        Args:
            table: Name of the table with merge conflicts.
            conflicts: Number of conflicting records.
        """
        self.table = table
        self.conflicts = conflicts
        super().__init__(f"Merge conflict in '{table}': {conflicts} conflicts")


# =============================================================================
# Authentication Errors
# =============================================================================


class AuthFailureError(CriticalError):
    """Raised when API authentication fails (401, 403).

    This is a CRITICAL error - pipeline should not continue without valid auth.

    Note:
        This differs from ServiceAuthenticationError (in network module) which
        is recoverable. AuthFailureError is for critical authentication failures
        where the pipeline cannot proceed at all.

    Attributes:
        provider: Name of the provider where authentication failed.
        status_code: Optional HTTP status code.

    Example:
        >>> raise AuthFailureError("uniprot", status_code=401)
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(self, provider: str, status_code: int | None = None) -> None:
        """Initialize AuthFailureError.

        Args:
            provider: Name of the provider where authentication failed.
            status_code: Optional HTTP status code.
        """
        self.provider = provider
        self.status_code = status_code
        msg = f"Authentication failed for {provider}"
        if status_code:
            msg += f" (HTTP {status_code})"
        super().__init__(msg)


# =============================================================================
# System Errors
# =============================================================================


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

    Example:
        >>> raise MetricsServerError(
        ...     port=8000,
        ...     reason="port_in_use",
        ...     original_error=OSError("Address already in use")
        ... )
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

    Example:
        >>> raise RunnerAlreadyExecutedError(
        ...     runner_type="CompositePipelineRunner",
        ...     run_id="run-123",
        ...     final_state="COMPLETED"
        ... )
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
