"""PipelineRun aggregate root for lifecycle tracking."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.events import (
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    PipelineRunState,
    StageResult,
    StageStatus,
    _PipelineRunStageMixin,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import JsonDict, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent

__all__ = [
    "PipelineRun",
    "PipelineRunState",
    "StageResult",
    "StageStatus",
]


class PipelineRun(_PipelineRunStageMixin):
    """Aggregate Root for pipeline execution.

    Invariants:
        1. status == COMPLETED only if all stages have status == SUCCESS
        2. status == FAILED if at least one stage has status == FAILED
        3. end_time != None only if status in (COMPLETED, FAILED, SHUTDOWN)
        4. stages cannot be modified after status is terminal
        5. run_id is unique and immutable after creation
    """

    __slots__ = (
        "_ended_at",
        "_events",
        "_manifest_id",
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
        manifest_id: str | None = None,
        metadata: JsonDict | None = None,
    ) -> None:
        """Initialize a new pipeline run."""
        self._run_id = run_id
        self._run_type = run_type
        self._pipeline_name = pipeline_name
        self._status = PipelineRunState.PENDING
        self._stages: list[StageResult] = []
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._events: list[DomainEvent] = []
        self._manifest_id = manifest_id
        self._metadata: JsonDict = deepcopy(metadata) if metadata is not None else {}

    def start(self, started_at: datetime) -> None:
        """Start the pipeline run at an explicit timestamp."""
        if self._status != PipelineRunState.PENDING:
            raise InvalidStateError(
                f"Cannot start run in status {self._status.value}",
                current_state=self._status.value,
                attempted_operation="start",
            )
        self._status = PipelineRunState.RUNNING
        self._started_at = started_at

    def complete(self, completed_at: datetime) -> None:
        """Mark run as COMPLETED if all stages succeeded."""
        self._assert_running("complete")
        self._assert_can_complete()
        self._status = PipelineRunState.COMPLETED
        self._ended_at = completed_at
        duration_seconds = 0.0
        if self._started_at is not None:
            duration_seconds = (completed_at - self._started_at).total_seconds()
        self._events.append(
            PipelineCompleted(
                occurred_at=completed_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=sum(
                    stage.records_processed for stage in self._stages
                ),
                duration_seconds=duration_seconds,
                stages_count=len(self._stages),
            )
        )

    def fail(
        self,
        error: str,
        error_type: str | None = None,
        *,
        failed_at: datetime,
    ) -> None:
        """Mark run as failed without stage-level details."""
        self._assert_running("fail")
        self._status = PipelineRunState.FAILED
        self._ended_at = failed_at
        self._events.append(
            PipelineFailed(
                occurred_at=failed_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                failed_stage="unknown",
                error=error,
                error_type=error_type,
            )
        )

    def shutdown(self, shutdown_at: datetime) -> None:
        """Mark the run as gracefully shutdown."""
        self._assert_running("shutdown")
        self._status = PipelineRunState.SHUTDOWN
        self._ended_at = shutdown_at
        self._events.append(
            PipelineShutdown(
                occurred_at=shutdown_at,
                run_id=self._run_id,
                pipeline_name=self._pipeline_name,
                records_processed=sum(
                    stage.records_processed for stage in self._stages
                ),
            )
        )

    def _assert_can_complete(self) -> None:
        self._assert_no_failed_stages()
        self._assert_has_recorded_stages()
        self._assert_all_stages_successful()

    def _assert_no_failed_stages(self) -> None:
        failed_stage_names = [
            stage.stage for stage in self._stages if stage.status == StageStatus.FAILED
        ]
        if failed_stage_names:
            raise InvalidStateError(
                f"Cannot complete run: {len(failed_stage_names)} stages failed: {failed_stage_names}",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def _assert_has_recorded_stages(self) -> None:
        if not self._stages:
            raise InvalidStateError(
                "Cannot complete run: no stages recorded",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    def _assert_all_stages_successful(self) -> None:
        incomplete_stage_names = [
            f"{stage.stage}:{stage.status.value}"
            for stage in self._stages
            if stage.status != StageStatus.SUCCESS
        ]
        if incomplete_stage_names:
            raise InvalidStateError(
                "Cannot complete run: "
                "all recorded stages must be SUCCESS before terminal completion; "
                f"found {incomplete_stage_names}",
                current_state=self._status.value,
                attempted_operation="complete",
            )

    @property
    def run_id(self) -> RunID:
        return self._run_id

    @property
    def run_type(self) -> RunType:
        return self._run_type

    @property
    def pipeline_name(self) -> str:
        return self._pipeline_name

    @property
    def status(self) -> PipelineRunState:
        return self._status

    @property
    def stages(self) -> tuple[StageResult, ...]:
        return tuple(self._stages)

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    @property
    def ended_at(self) -> datetime | None:
        return self._ended_at

    @property
    def metadata(self) -> JsonDict:
        return deepcopy(self._metadata)

    @property
    def manifest_id(self) -> str | None:
        return self._manifest_id

    @property
    def duration_seconds(self) -> float | None:
        if self._started_at is None or self._ended_at is None:
            return None
        return (self._ended_at - self._started_at).total_seconds()

    def duration_seconds_at(self, reference_time: datetime) -> float | None:
        if self._started_at is None:
            return None
        return ((self._ended_at or reference_time) - self._started_at).total_seconds()

    @property
    def total_records_processed(self) -> int:
        return sum(stage.records_processed for stage in self._stages)

    @property
    def failed_stages(self) -> tuple[StageResult, ...]:
        return tuple(
            stage for stage in self._stages if stage.status == StageStatus.FAILED
        )

    @property
    def successful_stages(self) -> tuple[StageResult, ...]:
        return tuple(
            stage for stage in self._stages if stage.status == StageStatus.SUCCESS
        )

    def collect_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events

    def __repr__(self) -> str:
        return (
            f"PipelineRun(run_id={self._run_id!r}, "
            f"status={self._status.value!r}, stages={len(self._stages)})"
        )
