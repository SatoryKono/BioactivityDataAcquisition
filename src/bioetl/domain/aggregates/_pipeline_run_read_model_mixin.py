# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Read-model mixins for PipelineRun aggregate."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.aggregates.pipeline_run_stage_result import StageResult
from bioetl.domain.aggregates.pipeline_run_state import PipelineRunState, StageStatus
from bioetl.domain.types import JsonDict, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.aggregates.events import DomainEvent


class _PipelineRunAttrs:
    """Typed private attributes shared by PipelineRun mixins."""

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

    _run_id: RunID  # pyright: ignore[reportUninitializedInstanceVariable]
    _run_type: RunType  # pyright: ignore[reportUninitializedInstanceVariable]
    _pipeline_name: str  # pyright: ignore[reportUninitializedInstanceVariable]
    _status: PipelineRunState  # pyright: ignore[reportUninitializedInstanceVariable]
    _stages: list[StageResult]  # pyright: ignore[reportUninitializedInstanceVariable]
    _started_at: datetime | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _ended_at: datetime | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _events: list[DomainEvent]  # pyright: ignore[reportUninitializedInstanceVariable]
    _manifest_id: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _metadata: JsonDict  # pyright: ignore[reportUninitializedInstanceVariable]


class _PipelineRunReadModelMixin(_PipelineRunAttrs):
    """Read model and event collection helpers for PipelineRun."""

    __slots__ = ()

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
    def status(self) -> PipelineRunState:
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
    def metadata(self) -> JsonDict:
        """Copy of run metadata."""
        return deepcopy(self._metadata)

    @property
    def manifest_id(self) -> str | None:
        """Optional control-plane manifest identifier associated with the run."""
        return self._manifest_id

    @property
    def duration_seconds(self) -> float | None:
        """Total run duration in seconds for completed runs."""
        if self._started_at is None:
            return None
        if self._ended_at is None:
            return None
        return (self._ended_at - self._started_at).total_seconds()

    def duration_seconds_at(self, reference_time: datetime) -> float | None:
        """Return run duration relative to an explicit reference time."""
        if self._started_at is None:
            return None
        end = self._ended_at or reference_time
        return (end - self._started_at).total_seconds()

    @property
    def total_records_processed(self) -> int:
        """Sum of records processed across all stages."""
        return sum(stage.records_processed for stage in self._stages)

    @property
    def failed_stages(self) -> tuple[StageResult, ...]:
        """Stages that failed."""
        return tuple(
            stage for stage in self._stages if stage.status == StageStatus.FAILED
        )

    @property
    def successful_stages(self) -> tuple[StageResult, ...]:
        """Stages that completed successfully."""
        return tuple(
            stage for stage in self._stages if stage.status == StageStatus.SUCCESS
        )

    def collect_events(self) -> list[DomainEvent]:
        """Collect and clear accumulated domain events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def __repr__(self) -> str:
        return (
            f"PipelineRun(run_id={self._run_id!r}, "
            f"status={self._status.value!r}, "
            f"stages={len(self._stages)})"
        )
