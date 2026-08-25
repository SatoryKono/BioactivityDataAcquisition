"""PipelineRun aggregate re-export facade for lifecycle tracking.

Re-export facade: implementation mixins are split into private modules
for maintainability while the public aggregate API remains stable.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._pipeline_run_mixins import (
    _PipelineRunLifecycleMixin,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    PipelineRunState,
    StageResult,
    StageStatus,
)
from bioetl.domain.types import JsonDict, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent

# StageResult invariants are enforced in StageResult.__post_init__ in
# pipeline_run_stage_result.py; this aggregate keeps the public import surface.
__all__ = [
    "PipelineRun",
    "PipelineRunState",
    "StageResult",
    "StageStatus",
]


class PipelineRun(_PipelineRunLifecycleMixin):
    """Aggregate Root for pipeline execution.

    Invariants:
        1. status == COMPLETED only if all stages have status == SUCCESS
        2. status == FAILED if at least one stage has status == FAILED
        3. end_time != None only if status in (COMPLETED, FAILED, SHUTDOWN)
        4. stages cannot be modified after status is terminal
        5. run_id is unique and immutable after creation
    """

    __slots__ = ()

    _run_id: RunID
    _run_type: RunType
    _pipeline_name: str
    _status: PipelineRunState
    _stages: list[StageResult]
    _started_at: datetime | None
    _ended_at: datetime | None
    _events: list[DomainEvent]
    _manifest_id: str | None
    _metadata: JsonDict

    def __init__(
        self,
        run_id: RunID,
        run_type: RunType,
        pipeline_name: str = "",
        manifest_id: str | None = None,
        metadata: JsonDict | None = None,
    ) -> None:
        """Initialize a new pipeline run.

        Args:
            run_id: Unique identifier for this pipeline execution.
            run_type: Type of run (incremental, backfill, rebuild).
            pipeline_name: Human-readable pipeline name (e.g., 'chembl_activity'). Defaults to ''.
            metadata: Optional key-value metadata to attach to the run.
        """
        self._run_id = run_id
        self._run_type = run_type
        self._pipeline_name = pipeline_name
        self._status = PipelineRunState.PENDING
        self._stages = []
        self._started_at = None
        self._ended_at = None
        self._events = []
        self._manifest_id = manifest_id
        self._metadata = deepcopy(metadata) if metadata is not None else {}

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
        return tuple(stage for stage in self._stages if stage.status == StageStatus.FAILED)

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
