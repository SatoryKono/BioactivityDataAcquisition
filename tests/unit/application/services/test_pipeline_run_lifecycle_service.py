"""Tests for PipelineRunLifecycleService orchestration API."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.services.execution.pipeline_run_lifecycle_service import (
    PipelineRunLifecycleService,
)
from bioetl.domain.aggregates.pipeline_run import PipelineRunState, StageStatus
from bioetl.domain.aggregates.pipeline_run import PipelineRun
from bioetl.domain.types import RunID, RunType


pytestmark = pytest.mark.unit

@pytest.fixture
def mock_clock() -> MagicMock:
    clock = MagicMock()
    clock.now.return_value = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    return clock


@pytest.fixture
def service(mock_clock: MagicMock) -> PipelineRunLifecycleService:
    return PipelineRunLifecycleService(clock=mock_clock)


@pytest.fixture
def run() -> PipelineRun:
    return PipelineRun(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        manifest_id="manifest-1",
    )


def test_start_and_complete_flow(
    service: PipelineRunLifecycleService,
    run: PipelineRun,
) -> None:
    start_at = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    complete_at = datetime(2026, 3, 7, 12, 5, tzinfo=UTC)

    service.start_run(run, started_at=start_at)
    service.stage_succeeded(
        run,
        "extract",
        result={"rows": 10},
        records_processed=10,
        started_at=start_at,
        completed_at=complete_at,
    )
    service.complete_run(run, completed_at=complete_at)

    assert run.status == PipelineRunState.COMPLETED
    assert run.started_at == start_at
    assert run.ended_at == complete_at
    assert len(run.stages) == 1
    assert run.stages[0].status == StageStatus.SUCCESS
    assert run.stages[0].records_processed == 10
    assert run.manifest_id == "manifest-1"


def test_stage_failed_marks_run_failed(
    service: PipelineRunLifecycleService,
    run: PipelineRun,
) -> None:
    service.start_run(run)
    service.stage_failed(
        run,
        "transform",
        error=ValueError("bad data"),
        error_type="validation",
    )

    assert run.status == PipelineRunState.FAILED
    assert len(run.stages) == 1
    assert run.stages[0].status == StageStatus.FAILED
    assert run.stages[0].error == "bad data"
    assert run.stages[0].error_type == "validation"


def test_start_run_uses_clock_when_timestamp_omitted(
    service: PipelineRunLifecycleService,
    run: PipelineRun,
    mock_clock: MagicMock,
) -> None:
    expected = datetime(2026, 3, 8, 9, 15, tzinfo=UTC)
    mock_clock.now.return_value = expected

    service.start_run(run)

    assert run.started_at == expected
    mock_clock.now.assert_called_once_with()


def test_fail_and_shutdown_helpers(
    service: PipelineRunLifecycleService,
) -> None:
    failed_run = PipelineRun(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
    )
    service.start_run(failed_run)
    service.fail_run(failed_run, error="manual stop", error_type="operator")
    assert failed_run.status == PipelineRunState.FAILED

    shutdown_run = PipelineRun(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
    )
    service.start_run(shutdown_run)
    service.shutdown_run(shutdown_run)
    assert shutdown_run.status == PipelineRunState.SHUTDOWN
