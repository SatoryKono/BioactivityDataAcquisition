"""Stage-level value objects for pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.aggregates.pipeline_run_state import StageStatus


def _validate_stage_name(stage: str) -> None:
    """Validate stage name is not empty."""
    if not stage:
        raise ValueError("Stage name cannot be empty")


def _validate_failed_has_error(status: StageStatus, error: str | None) -> None:
    if status != StageStatus.FAILED:
        return
    if error:
        return
    raise ValueError("Failed stage must have an error message")


def _validate_in_progress_no_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if status not in {StageStatus.PENDING, StageStatus.RUNNING}:
        return
    if completed_at is None:
        return
    raise ValueError(
        f"In-progress stage must not have completed_at timestamp, "
        f"got status={status.value}"
    )


def _validate_terminal_has_completion(
    status: StageStatus,
    completed_at: datetime | None,
) -> None:
    if status not in {StageStatus.SUCCESS, StageStatus.FAILED}:
        return
    if completed_at:
        return
    raise ValueError(
        f"Completed/Failed stage must have completed_at timestamp, "
        f"got status={status.value}"
    )


def _validate_completion_order(
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    if completed_at is None:
        return
    if completed_at >= started_at:
        return
    raise ValueError(
        "completed_at cannot be earlier than started_at: "
        f"started_at={started_at!s}, completed_at={completed_at!s}"
    )


def _validate_stage_completion(
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    started_at: datetime,
) -> None:
    """Validate stage completion invariants."""
    _validate_failed_has_error(status, error)
    _validate_in_progress_no_completion(status, completed_at)
    _validate_terminal_has_completion(status, completed_at)
    _validate_completion_order(completed_at, started_at)


def _validate_stage_result(
    stage: str,
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    records_processed: int,
    started_at: datetime,
) -> None:
    """Validate stage result invariants (extracted for lower CC)."""
    _validate_stage_name(stage)
    _validate_stage_completion(status, error, completed_at, started_at)
    if records_processed < 0:
        raise ValueError(f"records_processed cannot be negative: {records_processed}")


@dataclass(frozen=True, slots=True)
class StageResult:
    """Immutable value object representing the result of a pipeline stage.

    Attributes:
        stage: Name of the stage (e.g., "preflight", "execution", "postrun").
        status: Current status of the stage.
        started_at: Timestamp when stage started.
        completed_at: Timestamp when stage completed (None if still running).
        result: Optional result data from the stage.
        error: Error message if stage failed.
        error_type: Error classification if stage failed.
        records_processed: Number of records processed in this stage.
    """

    stage: str
    status: StageStatus
    started_at: datetime
    completed_at: datetime | None = None
    result: object = None
    error: str | None = None
    error_type: str | None = None
    records_processed: int = 0

    def __post_init__(self) -> None:
        """Validate stage result invariants."""
        _validate_stage_result(
            self.stage,
            self.status,
            self.error,
            self.completed_at,
            self.records_processed,
            self.started_at,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds for valid completions only."""
        if self.completed_at is None:
            return None
        if self.status in {StageStatus.PENDING, StageStatus.RUNNING}:
            return None
        duration = (self.completed_at - self.started_at).total_seconds()
        if duration < 0:
            return None
        return duration

    def with_success(
        self,
        completed_at: datetime,
        result: object = None,
        records_processed: int = 0,
    ) -> StageResult:
        """Create a new StageResult marking this stage as successful.

        Args:
            completed_at: Completion timestamp.
            result: Optional result data.
            records_processed: Number of records processed.

        Returns:
            New StageResult with SUCCESS status.
        """
        return StageResult(
            stage=self.stage,
            status=StageStatus.SUCCESS,
            started_at=self.started_at,
            completed_at=completed_at,
            result=result,
            records_processed=records_processed,
        )

    def with_failure(
        self,
        completed_at: datetime,
        error: str,
        error_type: str | None = None,
    ) -> StageResult:
        """Create a new StageResult marking this stage as failed.

        Args:
            completed_at: Completion timestamp.
            error: Error message.
            error_type: Error classification.

        Returns:
            New StageResult with FAILED status.
        """
        return StageResult(
            stage=self.stage,
            status=StageStatus.FAILED,
            started_at=self.started_at,
            completed_at=completed_at,
            error=error,
            error_type=error_type,
            records_processed=self.records_processed,
        )


__all__ = ["StageResult"]
