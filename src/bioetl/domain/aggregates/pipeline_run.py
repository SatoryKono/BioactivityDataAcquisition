"""PipelineRun aggregate re-export facade for lifecycle tracking.

Re-export facade: implementation mixins are split into private modules
for maintainability while the public aggregate API remains stable.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates._pipeline_run_mixins import (
    _PipelineRunLifecycleMixin,
    _PipelineRunReadModelMixin,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import StageResult
from bioetl.domain.aggregates.pipeline_run_state import PipelineRunState, StageStatus
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


class PipelineRun(_PipelineRunReadModelMixin, _PipelineRunLifecycleMixin):
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
        self._metadata = metadata or {}
