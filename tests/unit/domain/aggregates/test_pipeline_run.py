"""Tests for PipelineRun aggregate invariants.

Tests verify that:
1. status == COMPLETED only if all stages have status == SUCCESS
2. status == FAILED if at least one stage has status == FAILED
3. end_time != None only if status in (COMPLETED, FAILED, SHUTDOWN)
4. stages cannot be modified after status is terminal
5. run_id is unique and immutable after creation
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bioetl.domain.aggregates.pipeline_run import (
    PipelineRun,
    PipelineRunState,
    StageResult,
    StageStatus,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID, RunType
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(minutes: int = 0, seconds: int = 0) -> datetime:
    """Return a deterministic UTC timestamp for aggregate tests."""
    return datetime(2026, 3, 31, 12, minutes, seconds, tzinfo=UTC)


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("unit.pipeline_run.run_id"))


@pytest.fixture
def pipeline_run(run_id: RunID) -> PipelineRun:
    """Create a test pipeline run."""
    return PipelineRun(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="test_pipeline",
    )


@pytest.fixture
def started_run(pipeline_run: PipelineRun) -> PipelineRun:
    """Create a started pipeline run."""
    pipeline_run.start(_ts(0))
    return pipeline_run


# ──────────────────────────────────────────────────────────────────────────────
# StageResult Value Object Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestStageResultInvariants:
    """Tests for StageResult value object invariants."""

    def test_stage_name_cannot_be_empty(self) -> None:
        """Invariant: stage name is required."""
        with pytest.raises(ValueError, match="Stage name cannot be empty"):
            StageResult(
                stage="",
                status=StageStatus.SUCCESS,
                started_at=_ts(),
                completed_at=_ts(),
            )

    def test_failed_stage_must_have_error(self) -> None:
        """Invariant: failed stage requires error message."""
        with pytest.raises(ValueError, match="Failed stage must have an error"):
            StageResult(
                stage="test",
                status=StageStatus.FAILED,
                started_at=_ts(),
                completed_at=_ts(),
                error=None,  # Missing error
            )

    def test_completed_stage_must_have_completed_at(self) -> None:
        """Invariant: SUCCESS/FAILED stages require completed_at."""
        with pytest.raises(ValueError, match="must have completed_at"):
            StageResult(
                stage="test",
                status=StageStatus.SUCCESS,
                started_at=_ts(),
                completed_at=None,  # Missing timestamp
            )

    def test_records_processed_cannot_be_negative(self) -> None:
        """Invariant: records_processed >= 0."""
        with pytest.raises(ValueError, match="cannot be negative"):
            StageResult(
                stage="test",
                status=StageStatus.SUCCESS,
                started_at=_ts(),
                completed_at=_ts(),
                records_processed=-1,
            )

    def test_valid_stage_result_creation(self) -> None:
        """Valid StageResult should be created successfully."""
        now = _ts()
        stage = StageResult(
            stage="preflight",
            status=StageStatus.SUCCESS,
            started_at=now,
            completed_at=now + timedelta(seconds=5),
            records_processed=100,
        )
        assert stage.stage == "preflight"
        assert stage.status == StageStatus.SUCCESS
        assert stage.duration_seconds == pytest.approx(5.0)

    def test_pipeline_run_stage_result_is_immutable(self) -> None:
        """StageResult should be frozen (immutable)."""
        now = _ts()
        stage = StageResult(
            stage="test",
            status=StageStatus.SUCCESS,
            started_at=now,
            completed_at=now,
        )
        with pytest.raises(AttributeError):
            stage.stage = "modified"  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# PipelineRun State Transition Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunStateTransitions:
    """Tests for PipelineRun state machine transitions."""

    def test_initial_status_is_pending(self, pipeline_run: PipelineRun) -> None:
        """New run should be in PENDING status."""
        assert pipeline_run.status == PipelineRunState.PENDING
        assert pipeline_run.started_at is None
        assert pipeline_run.ended_at is None

    def test_start_transitions_to_running(self, pipeline_run: PipelineRun) -> None:
        """start() should transition PENDING -> RUNNING."""
        pipeline_run.start(_ts(0))
        assert pipeline_run.status == PipelineRunState.RUNNING
        assert pipeline_run.started_at == _ts(0)

    def test_cannot_start_already_running(self, started_run: PipelineRun) -> None:
        """Invariant: Cannot start a run that's already running."""
        with pytest.raises(InvalidStateError, match="Cannot start run"):
            started_run.start(_ts(1))

    def test_cannot_start_completed_run(self, started_run: PipelineRun) -> None:
        """Invariant: Cannot start a completed run."""
        started_run.record_stage_success("test", started_at=_ts(1), completed_at=_ts(2))
        started_run.complete(_ts(3))

        with pytest.raises(InvalidStateError, match="Cannot start run"):
            started_run.start(_ts(4))

    def test_running_duration_requires_explicit_reference(
        self, started_run: PipelineRun
    ) -> None:
        """Running duration should be computed only with an explicit reference time."""
        assert started_run.duration_seconds is None
        assert started_run.duration_seconds_at(_ts(seconds=5)) == pytest.approx(5.0)


class TestPipelineRunStageRecording:
    """Tests for stage recording behavior."""

    def test_record_stage_success(self, started_run: PipelineRun) -> None:
        """Should record successful stage."""
        started_run.record_stage_success(
            "preflight",
            result={"checks": 5},
            started_at=_ts(1),
            completed_at=_ts(2),
        )

        assert len(started_run.stages) == 1
        assert started_run.stages[0].stage == "preflight"
        assert started_run.stages[0].status == StageStatus.SUCCESS

    def test_cannot_record_stage_on_pending_run(
        self, pipeline_run: PipelineRun
    ) -> None:
        """Invariant: Cannot record stages on PENDING run."""
        with pytest.raises(InvalidStateError, match="run is in status pending"):
            pipeline_run.record_stage_success(
                "test",
                started_at=_ts(1),
                completed_at=_ts(2),
            )

    def test_record_stage_failure_transitions_to_failed(
        self, started_run: PipelineRun
    ) -> None:
        """Invariant: First stage failure transitions run to FAILED."""
        started_run.record_stage_failure(
            "execution",
            "Test error",
            started_at=_ts(1),
            completed_at=_ts(2),
        )

        assert started_run.status == PipelineRunState.FAILED
        assert started_run.ended_at is not None
        assert len(started_run.failed_stages) == 1

    def test_cannot_record_stages_after_failure(self, started_run: PipelineRun) -> None:
        """Invariant: Cannot record stages after run has failed."""
        started_run.record_stage_failure(
            "execution",
            "Test error",
            started_at=_ts(1),
            completed_at=_ts(2),
        )

        with pytest.raises(InvalidStateError, match="run is in status failed"):
            started_run.record_stage_success(
                "postrun",
                started_at=_ts(3),
                completed_at=_ts(4),
            )


# ──────────────────────────────────────────────────────────────────────────────
# Completion Invariants Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunCompletionInvariants:
    """Tests for completion invariants."""

    def test_cannot_complete_with_failed_stages(self, started_run: PipelineRun) -> None:
        """Invariant: complete() impossible with failed stages."""
        started_run.record_stage_success(
            "preflight",
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.record_stage_failure(
            "execution",
            ValueError("bad data"),
            started_at=_ts(3),
            completed_at=_ts(4),
        )

        # Run is already FAILED after stage failure
        with pytest.raises(InvalidStateError, match="Cannot complete"):
            started_run.complete(_ts(5))

    def test_cannot_complete_with_no_stages(self, started_run: PipelineRun) -> None:
        """Invariant: complete() requires at least one stage."""
        with pytest.raises(InvalidStateError, match="no stages recorded"):
            started_run.complete(_ts(1))

    def test_completed_run_has_stable_duration(self, started_run: PipelineRun) -> None:
        """Completed runs should expose deterministic duration from stored state."""
        started_run.record_stage_success(
            "preflight",
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.complete(_ts(seconds=6))

        assert started_run.duration_seconds == pytest.approx(6.0)
        assert started_run.duration_seconds_at(_ts(seconds=10)) == pytest.approx(6.0)

    def test_complete_with_all_successful_stages(
        self, started_run: PipelineRun
    ) -> None:
        """Should complete when all stages succeeded."""
        started_run.record_stage_success(
            "preflight",
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.record_stage_success(
            "execution",
            records_processed=1000,
            started_at=_ts(3),
            completed_at=_ts(4),
        )
        started_run.record_stage_success(
            "postrun",
            started_at=_ts(5),
            completed_at=_ts(6),
        )

        started_run.complete(_ts(7))

        assert started_run.status == PipelineRunState.COMPLETED
        assert started_run.ended_at is not None
        assert started_run.total_records_processed == 1000


# ──────────────────────────────────────────────────────────────────────────────
# Encapsulation Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunEncapsulation:
    """Tests for field encapsulation."""

    def test_run_encapsulation__modified_externally__78a9c339(
        self, pipeline_run: PipelineRun
    ) -> None:
        """Invariant: status changes only through aggregate methods."""
        with pytest.raises(AttributeError):
            pipeline_run.status = PipelineRunState.COMPLETED  # type: ignore

    def test_stages_returns_immutable_tuple(self, started_run: PipelineRun) -> None:
        """Invariant: stages property returns immutable copy."""
        started_run.record_stage_success(
            "test",
            started_at=_ts(1),
            completed_at=_ts(2),
        )

        stages = started_run.stages
        assert isinstance(stages, tuple)

        # Attempting to modify should fail
        with pytest.raises((TypeError, AttributeError)):
            stages.append(None)  # type: ignore

    def test_run_id_is_immutable(
        self, run_id: RunID, pipeline_run: PipelineRun
    ) -> None:
        """Invariant: run_id cannot be changed after creation."""
        assert pipeline_run.run_id == run_id

        with pytest.raises(AttributeError):
            pipeline_run.run_id = RunID(
                deterministic_uuid_value("unit.pipeline_run.mutability")
            )  # type: ignore

    def test_run_encapsulation__returns_copy__3ad406d4(self, run_id: RunID) -> None:
        """Invariant: metadata returns a copy, not the original."""
        original_metadata = {"key": "value"}
        run = PipelineRun(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            metadata=original_metadata,
        )

        # Modifying returned metadata shouldn't affect internal state
        metadata = run.metadata
        metadata["new_key"] = "new_value"

        assert "new_key" not in run.metadata


# ──────────────────────────────────────────────────────────────────────────────
# Domain Events Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunDomainEvents:
    """Tests for domain event generation."""

    def test_complete_emits_pipeline_completed_event(
        self, started_run: PipelineRun
    ) -> None:
        """complete() should emit PipelineCompleted event."""
        started_run.record_stage_success(
            "test",
            records_processed=100,
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.complete(_ts(3))

        events = started_run.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "PipelineCompleted"
        assert events[0].records_processed == 100

    def test_failure_emits_pipeline_failed_event(
        self, started_run: PipelineRun
    ) -> None:
        """Stage failure should emit PipelineFailed event."""
        started_run.record_stage_failure(
            "execution",
            "Test error",
            started_at=_ts(1),
            completed_at=_ts(2),
        )

        events = started_run.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "PipelineFailed"
        assert events[0].error == "Test error"

    def test_shutdown_emits_pipeline_shutdown_event(
        self, started_run: PipelineRun
    ) -> None:
        """shutdown() should emit PipelineShutdown event."""
        started_run.record_stage_success(
            "test",
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.shutdown(_ts(3))

        events = started_run.collect_events()
        assert len(events) == 1
        assert events[0].__class__.__name__ == "PipelineShutdown"

    def test_pipeline_run_domain_events_collect_events_clears_event_list(
        self, started_run: PipelineRun
    ) -> None:
        """collect_events() should clear internal list."""
        started_run.record_stage_success(
            "test",
            started_at=_ts(1),
            completed_at=_ts(2),
        )
        started_run.complete(_ts(3))

        first_collection = started_run.collect_events()
        second_collection = started_run.collect_events()

        assert len(first_collection) == 1
        assert len(second_collection) == 0


# ──────────────────────────────────────────────────────────────────────────────
# PipelineRunState Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunState:
    """Tests for PipelineRunState enum behavior."""

    def test_terminal_statuses(self) -> None:
        """Terminal statuses should return True for is_terminal()."""
        assert PipelineRunState.COMPLETED.is_terminal()
        assert PipelineRunState.FAILED.is_terminal()
        assert PipelineRunState.SHUTDOWN.is_terminal()

    def test_non_terminal_statuses(self) -> None:
        """Non-terminal statuses should return False for is_terminal()."""
        assert not PipelineRunState.PENDING.is_terminal()
        assert not PipelineRunState.RUNNING.is_terminal()
