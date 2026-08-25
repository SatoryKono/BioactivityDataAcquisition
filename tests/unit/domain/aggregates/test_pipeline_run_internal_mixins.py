# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for PipelineRun aggregate internal modules.

This test file provides focused coverage for PipelineRun internal modules:
- _pipeline_run_mixins.py: State transition methods and lifecycle operations
- _pipeline_run_read_model_mixin.py: Read model properties and event collection
- pipeline_run_stage_result.py: Stage result value objects and transformations

These tests complement the existing test_pipeline_run.py by testing internal
mixin methods directly and covering stage transformation scenarios.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.aggregates.pipeline_run import PipelineRun
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    StageResult,
    _validate_stage_completion,
    _validate_stage_name,
    _validate_stage_result,
)
from bioetl.domain.aggregates.pipeline_run_stage_result import (
    PipelineRunState,
    StageStatus,
)
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID, RunType
from tests.helpers.deterministic_ids import deterministic_uuid_value

pytestmark = pytest.mark.unit


def _ts(minutes: int = 0, seconds: int = 0) -> datetime:
    """Return a deterministic UTC timestamp for pipeline run tests."""
    return datetime(2026, 1, 1, 12, minutes, seconds, tzinfo=UTC)


def _ts_seconds(offset_seconds: int = 0) -> datetime:
    """Return a deterministic UTC timestamp with second-level precision."""
    return datetime(2026, 1, 1, 12, 0, offset_seconds, tzinfo=UTC)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(deterministic_uuid_value("pipeline_run_internal"))


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
# _pipeline_run_read_model_mixin.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunReadModelMixin:
    """Tests for _PipelineRunReadModelMixin properties and methods."""

    def test_pipeline_run_read_model_property_accessors_return_correct_values(
        self, run_id: RunID
    ):
        """Read model properties should return correct aggregate state."""
        pipeline_run = PipelineRun(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="test_pipeline",
            manifest_id="manifest-123",
            metadata={"key": "value"},
        )

        assert pipeline_run.run_id == run_id
        assert pipeline_run.run_type == RunType.INCREMENTAL
        assert pipeline_run.pipeline_name == "test_pipeline"
        assert pipeline_run.status == PipelineRunState.PENDING
        assert pipeline_run.manifest_id == "manifest-123"
        assert pipeline_run.metadata == {"key": "value"}
        assert pipeline_run.started_at is None
        assert pipeline_run.ended_at is None

    def test_stages_property_returns_immutable_tuple(self, pipeline_run: PipelineRun):
        """stages property should return immutable tuple."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )

        stages = pipeline_run.stages
        assert isinstance(stages, tuple)
        assert len(stages) == 1

        # Should not be modifiable
        with pytest.raises((TypeError, AttributeError)):
            stages.append(None)  # type: ignore

    def test_duration_seconds_returns_none_for_pending_run(
        self, pipeline_run: PipelineRun
    ):
        """duration_seconds should return None for runs without start/end times."""
        assert pipeline_run.duration_seconds is None

    def test_duration_seconds_at_returns_none_without_start(
        self, pipeline_run: PipelineRun
    ):
        """duration_seconds_at should return None when the run has not started."""
        assert pipeline_run.duration_seconds_at(_ts_seconds(15)) is None

    def test_duration_seconds_calculates_correct_duration(
        self, pipeline_run: PipelineRun
    ):
        """duration_seconds should calculate duration between start and end."""
        pipeline_run.start(_ts_seconds(0))
        pipeline_run.record_stage_success(
            "bronze",
            records_processed=100,
            started_at=_ts_seconds(0),
            completed_at=_ts_seconds(5),
        )
        pipeline_run.complete(_ts_seconds(10))

        assert pipeline_run.duration_seconds == 10.0

    def test_duration_seconds_at_uses_reference_time(self, pipeline_run: PipelineRun):
        """duration_seconds_at should calculate duration relative to reference time."""
        pipeline_run.start(_ts_seconds(0))

        duration = pipeline_run.duration_seconds_at(_ts_seconds(15))
        assert duration == 15.0

    def test_total_records_processed_sums_across_stages(
        self, pipeline_run: PipelineRun
    ):
        """total_records_processed should sum records from all stages."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.record_stage_success(
            "silver", records_processed=50, started_at=_ts(5), completed_at=_ts(10)
        )

        assert pipeline_run.total_records_processed == 150

    def test_failed_stages_filters_failed_stages(self, pipeline_run: PipelineRun):
        """failed_stages should return only failed stages."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.record_stage_failure(
            "silver",
            "Connection error",
            "TimeoutError",
            started_at=_ts(5),
            completed_at=_ts(10),
        )

        assert len(pipeline_run.failed_stages) == 1
        assert pipeline_run.failed_stages[0].stage == "silver"

    def test_successful_stages_filters_successful_stages(
        self, pipeline_run: PipelineRun
    ):
        """successful_stages should return only successful stages."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.record_stage_failure(
            "silver",
            "Connection error",
            "TimeoutError",
            started_at=_ts(5),
            completed_at=_ts(10),
        )

        assert len(pipeline_run.successful_stages) == 1
        assert pipeline_run.successful_stages[0].stage == "bronze"

    def test_pipeline_run_read_model_collect_events_clears_event_list(
        self, pipeline_run: PipelineRun
    ):
        """collect_events should return and clear accumulated events."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.complete(_ts(10))

        events = pipeline_run.collect_events()
        assert len(events) >= 1

        # Second call should return empty list
        events2 = pipeline_run.collect_events()
        assert len(events2) == 0

    def test_pipeline_run_read_model_repr_includes_key_state(
        self, pipeline_run: PipelineRun
    ):
        """__repr__ should include key aggregate state."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )

        repr_str = repr(pipeline_run)
        assert "PipelineRun(" in repr_str
        assert "status=" in repr_str
        assert "stages=1" in repr_str


# ──────────────────────────────────────────────────────────────────────────────
# _pipeline_run_mixins.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestPipelineRunLifecycleMixin:
    """Tests for _PipelineRunLifecycleMixin state transition methods."""

    def test_start_transitions_from_pending_to_running(self, pipeline_run: PipelineRun):
        """start should transition PENDING -> RUNNING."""
        assert pipeline_run.status == PipelineRunState.PENDING

        pipeline_run.start(_ts(0))

        assert pipeline_run.status == PipelineRunState.RUNNING
        assert pipeline_run.started_at == _ts(0)

    def test_start_validates_status(self, pipeline_run: PipelineRun):
        """start should only work from PENDING status."""
        pipeline_run.start(_ts(0))

        with pytest.raises(InvalidStateError, match="Cannot start"):
            pipeline_run.start(_ts(1))

    def test_start_invalid_after_terminal(self, pipeline_run: PipelineRun):
        """start() should fail once run reaches a terminal state."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(1), completed_at=_ts(2)
        )
        pipeline_run.complete(_ts(3))

        with pytest.raises(InvalidStateError, match="Cannot start"):
            pipeline_run.start(_ts(4))

    def test_record_stage_start_adds_running_stage(self, started_run: PipelineRun):
        """record_stage_start should add a RUNNING stage."""
        started_run.record_stage_start("bronze", _ts(0))

        assert len(started_run.stages) == 1
        assert started_run.stages[0].stage == "bronze"
        assert started_run.stages[0].status == StageStatus.RUNNING

    def test_record_stage_start_validates_running_status(
        self, pipeline_run: PipelineRun
    ):
        """record_stage_start should only work from RUNNING status."""
        with pytest.raises(InvalidStateError, match="Cannot record_stage_start"):
            pipeline_run.record_stage_start("bronze", _ts(0))

    def test_record_stage_success_adds_successful_stage(self, started_run: PipelineRun):
        """record_stage_success should add a SUCCESS stage."""
        started_run.record_stage_success(
            "bronze",
            result={"output": "data"},
            records_processed=100,
            started_at=_ts(0),
            completed_at=_ts(5),
        )

        assert len(started_run.stages) == 1
        stage = started_run.stages[0]
        assert stage.stage == "bronze"
        assert stage.status == StageStatus.SUCCESS
        assert stage.records_processed == 100
        assert stage.result == {"output": "data"}

    def test_record_stage_success_invalid_after_complete(
        self, started_run: PipelineRun
    ):
        """Cannot append stages after run is completed."""
        started_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(0), completed_at=_ts(1)
        )
        started_run.complete(_ts(2))

        with pytest.raises(InvalidStateError, match="Cannot record_stage_success"):
            started_run.record_stage_success(
                "silver", records_processed=1, started_at=_ts(2), completed_at=_ts(3)
            )

    def test_record_stage_failure_adds_failed_stage_and_fails_run(
        self, started_run: PipelineRun
    ):
        """record_stage_failure should add FAILED stage and transition run to FAILED."""
        started_run.record_stage_failure(
            "silver",
            "Connection timeout",
            "TimeoutError",
            started_at=_ts(0),
            completed_at=_ts(5),
        )

        assert len(started_run.stages) == 1
        stage = started_run.stages[0]
        assert stage.stage == "silver"
        assert stage.status == StageStatus.FAILED
        assert stage.error == "Connection timeout"
        assert stage.error_type == "TimeoutError"

        assert started_run.status == PipelineRunState.FAILED
        assert started_run.ended_at == _ts(5)

    def test_record_stage_failure_replaces_running_stage_entry(
        self, started_run: PipelineRun
    ) -> None:
        """record_stage_failure must replace RUNNING, not append (#8645)."""
        started_run.record_stage_start("silver", started_at=_ts(0))
        assert len(started_run.stages) == 1
        assert started_run.stages[0].status == StageStatus.RUNNING

        started_run.record_stage_failure(
            "silver",
            "boom",
            "RuntimeError",
            started_at=_ts(0),
            completed_at=_ts(5),
        )

        assert len(started_run.stages) == 1
        stage = started_run.stages[0]
        assert stage.stage == "silver"
        assert stage.status == StageStatus.FAILED
        assert stage.error == "boom"
        assert started_run.status == PipelineRunState.FAILED

    def test_record_stage_failure_with_exception_instance(
        self, started_run: PipelineRun
    ):
        """record_stage_failure should handle Exception instances."""
        error = ValueError("Invalid input")
        started_run.record_stage_failure(
            "bronze", error, "ValueError", started_at=_ts(0), completed_at=_ts(5)
        )

        stage = started_run.stages[0]
        assert stage.error == "Invalid input"

    def test_complete_transitions_to_completed(self, started_run: PipelineRun):
        """complete should transition RUNNING -> COMPLETED."""
        started_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        started_run.complete(_ts(10))

        assert started_run.status == PipelineRunState.COMPLETED
        assert started_run.ended_at == _ts(10)

    def test_complete_with_missing_started_at_uses_zero_duration(
        self, started_run: PipelineRun
    ):
        """complete should emit duration_seconds=0.0 when _started_at is None."""
        started_run._started_at = None
        started_run.record_stage_success(
            "bronze",
            records_processed=25,
            started_at=_ts(5),
            completed_at=_ts(15),
        )

        started_run.complete(_ts(20))
        events = started_run.collect_events()

        assert started_run.status == PipelineRunState.COMPLETED
        assert started_run.duration_seconds is None
        assert len(events) == 1
        assert events[0].duration_seconds == 0.0

    def test_complete_blocks_when_any_stage_failed_but_status_still_running(
        self, pipeline_run: PipelineRun
    ):
        """complete should reject terminal transition if failed stages are present."""
        pipeline_run.start(_ts(0))
        pipeline_run._stages.append(
            StageResult(
                stage="bronze",
                status=StageStatus.FAILED,
                started_at=_ts(1),
                completed_at=_ts(2),
                error="manual failed stage",
                error_type="Manual",
            )
        )

        with pytest.raises(InvalidStateError, match="Cannot complete"):
            pipeline_run.complete(_ts(10))

    def test_complete_blocks_when_any_stage_is_not_success(
        self, started_run: PipelineRun
    ) -> None:
        """complete should reject RUNNING stage entries that have not reached SUCCESS."""
        started_run.record_stage_start("bronze", started_at=_ts(1))

        with pytest.raises(InvalidStateError, match="must be SUCCESS"):
            started_run.complete(_ts(10))

    def test_complete_validates_running_status(self, pipeline_run: PipelineRun):
        """complete should only work from RUNNING status."""
        with pytest.raises(InvalidStateError, match="Cannot complete"):
            pipeline_run.complete(_ts(10))

    def test_complete_invalid_after_shutdown(self, started_run: PipelineRun):
        """complete() should fail after shutdown."""
        started_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(1), completed_at=_ts(2)
        )
        started_run.shutdown(_ts(5))

        with pytest.raises(InvalidStateError, match="Cannot complete"):
            started_run.complete(_ts(6))

    def test_complete_validates_no_failed_stages(self, started_run: PipelineRun):
        """complete should fail if any stages failed."""
        # Note: record_stage_failure automatically transitions run to FAILED status,
        # so the _assert_running check happens before the _assert_can_complete check.
        # This test verifies that the run is in FAILED status after stage failure.
        started_run.record_stage_failure(
            "bronze", "Error", "ERR", started_at=_ts(0), completed_at=_ts(5)
        )

        assert started_run.status == PipelineRunState.FAILED
        # Cannot complete a failed run
        with pytest.raises(InvalidStateError, match="Cannot complete"):
            started_run.complete(_ts(10))

    def test_complete_validates_has_stages(self, started_run: PipelineRun):
        """complete should fail if no stages were recorded."""
        with pytest.raises(InvalidStateError, match="no stages recorded"):
            started_run.complete(_ts(10))

    def test_fail_invalid_after_complete(self, started_run: PipelineRun):
        """Cannot fail once run is completed."""
        started_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(1), completed_at=_ts(2)
        )
        started_run.complete(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot fail"):
            started_run.fail("late failure", failed_at=_ts(11))

    def test_shutdown_invalid_after_complete(self, started_run: PipelineRun):
        """Cannot shutdown once run is completed."""
        started_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(1), completed_at=_ts(2)
        )
        started_run.complete(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot shutdown"):
            started_run.shutdown(_ts(11))

    def test_fail_transitions_to_failed(self, started_run: PipelineRun):
        """fail should transition RUNNING -> FAILED."""
        started_run.fail("Pipeline error", "RuntimeError", failed_at=_ts(10))

        assert started_run.status == PipelineRunState.FAILED
        assert started_run.ended_at == _ts(10)

    def test_fail_invalid_after_shutdown(self, started_run: PipelineRun):
        """Cannot fail once run is shutdown."""
        started_run.record_stage_success(
            "bronze", records_processed=1, started_at=_ts(1), completed_at=_ts(2)
        )
        started_run.shutdown(_ts(4))

        with pytest.raises(InvalidStateError, match="Cannot fail"):
            started_run.fail("retry", failed_at=_ts(5))

    def test_fail_validates_running_status(self, pipeline_run: PipelineRun):
        """fail should only work from RUNNING status."""
        with pytest.raises(InvalidStateError, match="Cannot fail"):
            pipeline_run.fail("Error", None, failed_at=_ts(10))

    def test_shutdown_transitions_to_shutdown(self, started_run: PipelineRun):
        """shutdown should transition RUNNING -> SHUTDOWN."""
        started_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        started_run.shutdown(_ts(10))

        assert started_run.status == PipelineRunState.SHUTDOWN
        assert started_run.ended_at == _ts(10)

    def test_shutdown_validates_running_status(self, pipeline_run: PipelineRun):
        """shutdown should only work from RUNNING status."""
        with pytest.raises(InvalidStateError, match="Cannot shutdown"):
            pipeline_run.shutdown(_ts(10))

    def test_assert_running_blocks_non_running_states(self, pipeline_run: PipelineRun):
        """_assert_running should raise InvalidStateError for non-RUNNING states."""
        # PENDING
        with pytest.raises(InvalidStateError, match="Cannot record_stage_start"):
            pipeline_run.record_stage_start("bronze", _ts(0))

        # After completion
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.complete(_ts(10))

        with pytest.raises(InvalidStateError, match="Cannot record_stage_start"):
            pipeline_run.record_stage_start("silver", _ts(15))


# ──────────────────────────────────────────────────────────────────────────────
# pipeline_run_stage_result.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestStageResultValidationFunctions:
    """Tests for StageResult validation functions."""

    def test_validate_stage_name_rejects_empty(self):
        """_validate_stage_name should reject empty stage names."""
        with pytest.raises(ValueError, match="Stage name cannot be empty"):
            _validate_stage_name("")

    def test_validate_stage_name_accepts_valid(self):
        """_validate_stage_name should accept valid stage names."""
        _validate_stage_name("bronze")  # Should not raise

    def test_validate_stage_completion_failed_requires_error(self):
        """_validate_stage_completion should require error for FAILED status."""
        with pytest.raises(ValueError, match="Failed stage must have an error"):
            _validate_stage_completion(StageStatus.FAILED, None, _ts(0), _ts(0))

    def test_validate_stage_completion_success_requires_timestamp(self):
        """_validate_stage_completion should require completed_at for SUCCESS."""
        with pytest.raises(ValueError, match="must have completed_at"):
            _validate_stage_completion(StageStatus.SUCCESS, None, None, _ts(0))

    def test_validate_stage_completion_failed_requires_timestamp(self):
        """_validate_stage_completion should require completed_at for FAILED."""
        with pytest.raises(ValueError, match="must have completed_at"):
            _validate_stage_completion(StageStatus.FAILED, "error", None, _ts(0))

    def test_validate_stage_completion_running_allows_none_timestamp(self):
        """_validate_stage_completion should allow None for RUNNING status."""
        _validate_stage_completion(
            StageStatus.RUNNING, None, None, _ts(0)
        )  # Should not raise

    def test_validate_stage_result_rejects_negative_records(self):
        """_validate_stage_result should reject negative records_processed."""
        with pytest.raises(ValueError, match="cannot be negative"):
            _validate_stage_result(
                "test", StageStatus.SUCCESS, None, _ts(0), -1, _ts(0)
            )


class TestStageResultValueObject:
    """Tests for StageResult value object methods."""

    def test_stage_result_duration_seconds_for_completed_stage(self):
        """duration_seconds should calculate duration for completed stages."""
        stage = StageResult(
            stage="bronze",
            status=StageStatus.SUCCESS,
            started_at=_ts_seconds(0),
            completed_at=_ts_seconds(10),
        )

        assert stage.duration_seconds == 10.0

    def test_stage_result_duration_seconds_for_running_stage(self):
        """duration_seconds should return None for running stages."""
        stage = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
            completed_at=None,
        )

        assert stage.duration_seconds is None

    def test_with_success_creates_successful_copy(self):
        """with_success should create a SUCCESS copy of the stage."""
        running = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
        )

        completed = running.with_success(
            _ts(10), result={"output": "data"}, records_processed=100
        )

        assert completed.status == StageStatus.SUCCESS
        assert completed.completed_at == _ts(10)
        assert completed.result == {"output": "data"}
        assert completed.records_processed == 100
        assert completed.stage == running.stage
        assert completed.started_at == running.started_at

    def test_with_failure_creates_failed_copy(self):
        """with_failure should create a FAILED copy of the stage."""
        running = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
            records_processed=50,
        )

        failed = running.with_failure(_ts(10), "Connection error", "TimeoutError")

        assert failed.status == StageStatus.FAILED
        assert failed.completed_at == _ts(10)
        assert failed.error == "Connection error"
        assert failed.error_type == "TimeoutError"
        assert failed.records_processed == 50  # Preserved
        assert failed.stage == running.stage
        assert failed.started_at == running.started_at

    def test_pipeline_run_internal_stage_result_is_immutable(self):
        """StageResult should be frozen (immutable)."""
        stage = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
        )

        with pytest.raises(AttributeError):
            stage.status = StageStatus.SUCCESS  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# Stage Sequence Integration Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestStageSequences:
    """Integration tests for stage sequences covering success/failure/shutdown scenarios."""

    def test_successful_stage_sequence(self, pipeline_run: PipelineRun):
        """Test complete successful sequence: start -> stages -> complete."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.record_stage_success(
            "silver", records_processed=50, started_at=_ts(5), completed_at=_ts(10)
        )
        pipeline_run.complete(_ts(15))

        assert pipeline_run.status == PipelineRunState.COMPLETED
        assert len(pipeline_run.successful_stages) == 2
        assert len(pipeline_run.failed_stages) == 0
        assert pipeline_run.total_records_processed == 150

    def test_stage_failure_sequence(self, pipeline_run: PipelineRun):
        """Test failure sequence: start -> success -> failure -> failed."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.record_stage_failure(
            "silver",
            "Connection error",
            "TimeoutError",
            started_at=_ts(5),
            completed_at=_ts(10),
        )

        assert pipeline_run.status == PipelineRunState.FAILED
        assert len(pipeline_run.successful_stages) == 1
        assert len(pipeline_run.failed_stages) == 1

    def test_shutdown_sequence(self, pipeline_run: PipelineRun):
        """Test shutdown sequence: start -> partial success -> shutdown."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.shutdown(_ts(10))

        assert pipeline_run.status == PipelineRunState.SHUTDOWN
        assert len(pipeline_run.successful_stages) == 1
        assert pipeline_run.ended_at == _ts(10)

    def test_idempotency_prevents_duplicate_operations(self, pipeline_run: PipelineRun):
        """Test that state transitions are idempotent and prevent invalid sequences."""
        pipeline_run.start(_ts(0))

        # Cannot start again
        with pytest.raises(InvalidStateError):
            pipeline_run.start(_ts(1))

        pipeline_run.record_stage_success(
            "bronze", records_processed=100, started_at=_ts(0), completed_at=_ts(5)
        )
        pipeline_run.complete(_ts(10))

        # Cannot record stages after completion
        with pytest.raises(InvalidStateError):
            pipeline_run.record_stage_success(
                "silver", records_processed=50, started_at=_ts(10), completed_at=_ts(15)
            )

        # Cannot complete again
        with pytest.raises(InvalidStateError):
            pipeline_run.complete(_ts(20))

    def test_running_stage_to_success_transformation(self, pipeline_run: PipelineRun):
        """Test transforming a running stage to successful completion."""
        pipeline_run.start(_ts(0))
        pipeline_run.record_stage_start("bronze", _ts(0))

        running_stage = pipeline_run.stages[0]
        assert running_stage.status == StageStatus.RUNNING

        # Simulate stage completion by recording success
        pipeline_run.record_stage_success(
            "silver", records_processed=100, started_at=_ts(5), completed_at=_ts(10)
        )

        # Original stage remains RUNNING, new stage is SUCCESS
        assert pipeline_run.stages[0].status == StageStatus.RUNNING
        assert pipeline_run.stages[1].status == StageStatus.SUCCESS

    def test_stage_result_with_success_transformation(self):
        """Test StageResult.with_success transformation."""
        running = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
        )

        success = running.with_success(
            _ts(10), result={"data": "value"}, records_processed=100
        )

        # Original should be unchanged (immutable)
        assert running.status == StageStatus.RUNNING
        assert running.completed_at is None

        # New copy should be SUCCESS
        assert success.status == StageStatus.SUCCESS
        assert success.completed_at == _ts(10)
        assert success.records_processed == 100

    def test_stage_result_with_failure_transformation(self):
        """Test StageResult.with_failure transformation."""
        running = StageResult(
            stage="bronze",
            status=StageStatus.RUNNING,
            started_at=_ts(0),
            records_processed=50,
        )

        failed = running.with_failure(_ts(10), "Error message", "ErrorType")

        # Original should be unchanged (immutable)
        assert running.status == StageStatus.RUNNING
        assert running.error is None

        # New copy should be FAILED
        assert failed.status == StageStatus.FAILED
        assert failed.error == "Error message"
        assert failed.error_type == "ErrorType"
        assert failed.records_processed == 50  # Preserved
