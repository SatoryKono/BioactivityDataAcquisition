"""Property-based invariant tests for the PipelineRun aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from bioetl.domain.aggregates.pipeline_run import PipelineRun, PipelineRunState
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.types import RunID, RunType

pytestmark = [pytest.mark.hypothesis]

_STAGE_NAME = st.text(
    min_size=1,
    max_size=16,
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"),
        whitelist_characters="-_",
    ),
)
_SUCCESS_STAGE_PLAN = st.lists(
    st.tuples(_STAGE_NAME, st.integers(min_value=0, max_value=10_000)),
    min_size=1,
    max_size=6,
    unique_by=lambda item: item[0],
)


def _ts(offset_seconds: int = 0) -> datetime:
    return datetime(2026, 4, 24, 12, 0, tzinfo=UTC) + timedelta(
        seconds=offset_seconds
    )


def _run_id() -> RunID:
    return RunID(uuid4())


def _make_run() -> PipelineRun:
    return PipelineRun(
        run_id=_run_id(),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
    )


class TestPipelineRunInvariantProperties:
    """Invariant-focused properties for PipelineRun FSM laws."""

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(stage_plan=_SUCCESS_STAGE_PLAN)
    def test_success_only_stage_sequences_can_complete(
        self,
        stage_plan: list[tuple[str, int]],
    ) -> None:
        """Runs with only successful stages must complete and preserve totals."""
        run = _make_run()
        run.start(_ts(0))

        for index, (stage_name, records_processed) in enumerate(stage_plan, start=1):
            run.record_stage_success(
                stage_name,
                records_processed=records_processed,
                started_at=_ts(index * 2 - 1),
                completed_at=_ts(index * 2),
            )

        completed_at = _ts(len(stage_plan) * 2 + 1)
        run.complete(completed_at)

        assert run.status == PipelineRunState.COMPLETED
        assert run.ended_at == completed_at
        assert len(run.stages) == len(stage_plan)
        assert len(run.successful_stages) == len(stage_plan)
        assert run.failed_stages == ()
        assert run.total_records_processed == sum(
            records_processed for _, records_processed in stage_plan
        )
        assert run.duration_seconds == pytest.approx(
            (completed_at - _ts(0)).total_seconds()
        )

    @pytest.mark.hypothesis
    @settings(
        deadline=None,
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        success_prefix=_SUCCESS_STAGE_PLAN,
        failing_stage=_STAGE_NAME,
    )
    def test_failed_stage_is_terminal_and_blocks_completion(
        self,
        success_prefix: list[tuple[str, int]],
        failing_stage: str,
    ) -> None:
        """Any failed stage must push the run into terminal FAILED state."""
        success_stage_names = {stage_name for stage_name, _ in success_prefix}
        assume(failing_stage not in success_stage_names)

        run = _make_run()
        run.start(_ts(0))

        for index, (stage_name, records_processed) in enumerate(success_prefix, start=1):
            run.record_stage_success(
                stage_name,
                records_processed=records_processed,
                started_at=_ts(index * 2 - 1),
                completed_at=_ts(index * 2),
            )

        failure_offset = len(success_prefix) * 2 + 1
        run.record_stage_failure(
            failing_stage,
            "stage failure",
            started_at=_ts(failure_offset),
            completed_at=_ts(failure_offset + 1),
        )

        assert run.status == PipelineRunState.FAILED
        assert run.ended_at == _ts(failure_offset + 1)
        assert len(run.failed_stages) == 1
        assert run.failed_stages[0].stage == failing_stage

        with pytest.raises(InvalidStateError, match="Cannot complete"):
            run.complete(_ts(failure_offset + 2))

        with pytest.raises(InvalidStateError, match="run is in status failed"):
            run.record_stage_success(
                "post_failure",
                started_at=_ts(failure_offset + 3),
                completed_at=_ts(failure_offset + 4),
            )

    def test_regression_cannot_complete_without_recorded_stages(self) -> None:
        """A RUNNING run without stages must not transition to COMPLETED."""
        run = _make_run()
        run.start(_ts(0))

        with pytest.raises(InvalidStateError, match="no stages recorded"):
            run.complete(_ts(1))
