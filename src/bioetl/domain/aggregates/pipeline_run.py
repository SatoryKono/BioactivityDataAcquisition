"""PipelineRun Aggregate for pipeline execution tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID, RunType


class StageStatus(str, Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Status of a pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

    def is_terminal(self) -> bool:
        """Check if terminal (no more transitions)."""
        return self in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.SHUTDOWN}


def _validate_stage_name(stage: str) -> None:
    """Validate stage name is not empty."""
    if not stage:
        raise ValueError("Stage name cannot be empty")


def _validate_stage_completion(
    status: StageStatus, error: str | None, completed_at: datetime | None
) -> None:
    """Validate stage completion invariants."""
    if status == StageStatus.FAILED and not error:
        raise ValueError("Failed stage must have an error message")
    needs_timestamp = status in {StageStatus.SUCCESS, StageStatus.FAILED}
    if needs_timestamp and not completed_at:
        raise ValueError(
            f"Completed/Failed stage must have completed_at timestamp, "
            f"got status={status.value}"
        )


def _validate_stage_result(
    stage: str,
    status: StageStatus,
    error: str | None,
    completed_at: datetime | None,
    records_processed: int,
) -> None:
    """Validate stage result invariants (extracted for lower CC)."""
    _validate_stage_name(stage)
    _validate_stage_completion(status, error, completed_at)
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
    result: Any = None
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
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate stage duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def with_success(
        self,
        completed_at: datetime,
        result: Any = None,
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


class PipelineRun:
    """Aggregate Root for pipeline execution.

    Invariants:
        1. status == COMPLETED only if all stages have status == SUCCESS
        2. status == FAILED if at least one stage has status == FAILED
        3. end_time != None only if status in (COMPLETED, FAILED, SHUTDOWN)
        4. stages cannot be modified after status is terminal
        5. run_id is unique and immutable after creation

    Consistency Boundary:
        - Stages and status changes are transactionally consistent
        - Domain events are collected and published after state changes

    Example:
        >>> run = PipelineRun(run_id=run_id, run_type=RunType.INCREMENTAL)
        >>> run.start()
        >>> run.record_stage_success("preflight", result={"checks": 5})
        >>> run.record_stage_success("execution", records_processed=1000)
        >>> run.complete()
        >>> events = run.collect_events()
    """

    __slots__ = (
        "_ended_at",
        "_events",
        "_metadata",
        "_pipeline_name",
        "_run_id",
        "_run_type",
        "_stages",
        "_started_at",
        "_status",
    )

    def __init__(
        self,
        run_id: RunID,
        run_type: RunType,
        pipeline_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a new pipeline run.

        Args:
            run_id: Unique identifier for this run.
            run_type: Type of run (incremental, backfill, rebuild).
            pipeline_name: Name of the pipeline being executed.
            metadata: Optional additional metadata.
        """
        self._run_id = run_id
        self._run_type = run_type
        self._pipeline_name = pipeline_name
        self._status = RunStatus.PENDING
        self._stages: list[StageResult] = []
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._events: list[Any] = []
        self._metadata = metadata or {}

    @property
    def run_id(self) -> RunID:
        """Immutable run identifier."""
        return self._run_id

    @property
    def run_type(self) -> RunType:
        """Type of pipeline run."""
        return self._run_type

    @property
    def pipeline_name(self) -> str:
        """Name of the pipeline."""
        return self._pipeline_name

    @property
    def status(self) -> RunStatus:
        """Current run status (read-only)."""
        return self._status

    @property
    def stages(self) -> tuple[StageResult, ...]:
        """Immutable tuple of stage results."""
        return tuple(self._stages)

    @property
    def started_at(self) -> datetime | None:
        """Timestamp when run started."""
        return self._started_at

    @property
    def ended_at(self) -> datetime | None:
        """Timestamp when run ended (completed, failed, or shutdown)."""
        return self._ended_at

    @property
    def metadata(self) -> dict[str, Any]:
        """Copy of run metadata."""
        return self._metadata.copy()

    @property
    def duration_seconds(self) -> float | None:
        """Total run duration in seconds."""
        if self._started_at is None:
            return None
        end = self._ended_at or datetime.now(UTC)
        return (end - self._started_at).total_seconds()

    @property
    def total_records_processed(self) -> int:
        """Sum of records processed across all stages."""
        return sum(s.records_processed for s in self._stages)

    @property
    def failed_stages(self) -> tuple[StageResult, ...]:
        """Stages that failed."""
        return tuple(s for s in self._stages if s.status == StageStatus.FAILED)

    @property
    def successful_stages(self) -> tuple[StageResult, ...]:
        """Stages that completed successfully."""
        return tuple(s for s in self._stages if s.status == StageStatus.SUCCESS)

    def start(self, started_at: datetime | None = None) -> None:
        """Start the pipeline run.

        Transitions: PENDING -> RUNNING

        Args:
            started_at: Optional start timestamp. Uses current UTC time if not provided.

        Raises:
            InvalidStateError: If run is not in PENDING status.
        """
        if self._status != RunStatus.PENDING:
            raise InvalidStateError(
                f"Cannot start run in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="start",
            )
        self._status = RunStatus.RUNNING
        self._started_at = started_at or datetime.now(UTC)

    def record_stage_start(
        self, stage: str, started_at: datetime | None = None
    ) -> None:
        """Record the start of a pipeline stage.

        Args:
            stage: Name of the stage.
            started_at: Optional start timestamp.

        Raises:
            InvalidStateError: If run is not in RUNNING status.
        """
        self._assert_running("record_stage_start")
        self._stages.append(
            StageResult(
                stage=stage,
                status=StageStatus.RUNNING,
                started_at=started_at or datetime.now(UTC),
            )
        )

    def record_stage_success(
        self,
        stage: str,
        result: Any = None,
        records_processed: int = 0,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record successful completion of a pipeline stage.

        Args:
            stage: Name of the stage.
            result: Optional result data from the stage.
            records_processed: Number of records processed.
            started_at: Stage start timestamp (uses current time if not provided).
            completed_at: Stage completion timestamp (uses current time if not provided).

        Raises:
            InvalidStateError: If run is not in RUNNING status.
        """
        self._assert_running("record_stage_success")
        now = datetime.now(UTC)
        self._stages.append(
            StageResult(
                stage=stage,
                status=StageStatus.SUCCESS,
                started_at=started_at or now,
                completed_at=completed_at or now,
                result=result,
                records_processed=records_processed,
            )
        )

    def record_stage_failure(
        self,
        stage: str,
        error: str | Exception,
        error_type: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Record failure of a pipeline stage.

        Transitions: RUNNING -> FAILED (immediately upon first stage failure)

        Args:
            stage: Name of the stage.
            error: Error message or exception.
            error_type: Error classification.
            started_at: Stage start timestamp.
            completed_at: Stage completion timestamp.

        Raises:
            InvalidStateError: If run is not in RUNNING status.
        """
        self._assert_running("record_stage_failure")
        now = datetime.now(UTC)
        error_msg = str(error) if isinstance(error, Exception) else error

        self._stages.append(
            StageResult(
                stage=stage,
                status=StageStatus.FAILED,
                started_at=started_at or now,
                completed_at=completed_at or now,
                error=error_msg,
                error_type=error_type,
            )
        )

        # Invariant: First stage failure transitions run to FAILED
        self._status = RunStatus.FAILED
        self._ended_at = completed_at or now

        # Emit domain event
        from bioetl.domain.aggregates.events import PipelineFailed

        self._events.append(
            PipelineFailed(
                occurred_at=self._ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage=stage,
                error=error_msg,
                error_type=error_type,
            )
        )

    def _assert_can_complete(self) -> None:
        """Check invariants required for successful completion."""
        if self.failed_stages:
            failed_names = [s.stage for s in self.failed_stages]
            raise InvalidStateError(
                f"Cannot complete run: {len(self.failed_stages)} stages failed: {failed_names}",
                current_state=self._status.value,
                attempted_operation="complete",
            )
        if not self._stages:
            raise InvalidStateError(
                "Cannot complete run: no stages recorded",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def complete(self, completed_at: datetime | None = None) -> None:
        """Mark the run as completed successfully.

        Transitions: RUNNING -> COMPLETED

        Invariants checked:
            - All recorded stages must have SUCCESS status
            - At least one stage must be recorded

        Args:
            completed_at: Completion timestamp.

        Raises:
            InvalidStateError: If run is not RUNNING, has failed stages,
                             or has no stages.
        """
        self._assert_running("complete")
        self._assert_can_complete()

        now = completed_at or datetime.now(UTC)
        self._status = RunStatus.COMPLETED
        self._ended_at = now

        # Emit domain event
        from bioetl.domain.aggregates.events import PipelineCompleted

        self._events.append(
            PipelineCompleted(
                occurred_at=self._ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=self.total_records_processed,
                duration_seconds=self.duration_seconds or 0.0,
                stages_count=len(self._stages),
            )
        )

    def fail(
        self,
        error: str,
        error_type: str | None = None,
        failed_at: datetime | None = None,
    ) -> None:
        """Mark the run as failed without recording a specific stage.

        Transitions: RUNNING -> FAILED

        Args:
            error: Error message.
            error_type: Error classification.
            failed_at: Failure timestamp.

        Raises:
            InvalidStateError: If run is not in RUNNING status.
        """
        self._assert_running("fail")
        now = failed_at or datetime.now(UTC)
        self._status = RunStatus.FAILED
        self._ended_at = now

        # Emit domain event
        from bioetl.domain.aggregates.events import PipelineFailed

        self._events.append(
            PipelineFailed(
                occurred_at=self._ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage="unknown",
                error=error,
                error_type=error_type,
            )
        )

    def shutdown(self, shutdown_at: datetime | None = None) -> None:
        """Mark the run as gracefully shutdown.

        Transitions: RUNNING -> SHUTDOWN

        Args:
            shutdown_at: Shutdown timestamp.

        Raises:
            InvalidStateError: If run is not in RUNNING status.
        """
        self._assert_running("shutdown")
        now = shutdown_at or datetime.now(UTC)
        self._status = RunStatus.SHUTDOWN
        self._ended_at = now

        # Emit domain event
        from bioetl.domain.aggregates.events import PipelineShutdown

        self._events.append(
            PipelineShutdown(
                occurred_at=self._ended_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=self.total_records_processed,
            )
        )

    def collect_events(self) -> list[Any]:
        """Collect and clear accumulated domain events.

        Returns:
            List of domain events. Clears internal event list.
        """
        events = self._events.copy()
        self._events.clear()
        return events

    def _assert_running(self, operation: str) -> None:
        """Assert that the run is in RUNNING status.

        Raises:
            InvalidStateError: If not in RUNNING status.
        """
        if self._status != RunStatus.RUNNING:
            raise InvalidStateError(
                f"Cannot {operation}: run is in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation=operation,
            )

    def __repr__(self) -> str:
        return (
            f"PipelineRun(run_id={self._run_id!r}, "
            f"status={self._status.value!r}, "
            f"stages={len(self._stages)})"
        )
