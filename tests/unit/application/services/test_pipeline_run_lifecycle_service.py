# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for PipelineRunLifecycleService orchestration API."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.execution.pipeline_run_lifecycle_service import (
    PipelineRunLifecycleService,
)
from bioetl.domain.aggregates.pipeline_run import PipelineRunState, StageStatus
from bioetl.domain.aggregates.pipeline_run import PipelineRun
from bioetl.domain.types import RunID, RunType


pytestmark = pytest.mark.unit

RUN_FIXTURE_ID = UUID("11111111-1111-4111-8111-111111111111")
FAILED_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
SHUTDOWN_RUN_ID = UUID("33333333-3333-4333-8333-333333333333")


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
        run_id=RunID(RUN_FIXTURE_ID),
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
        run_id=RunID(FAILED_RUN_ID),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
    )
    service.start_run(failed_run)
    service.fail_run(failed_run, error="manual stop", error_type="operator")
    assert failed_run.status == PipelineRunState.FAILED

    shutdown_run = PipelineRun(
        run_id=RunID(SHUTDOWN_RUN_ID),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
    )
    service.start_run(shutdown_run)
    service.shutdown_run(shutdown_run)
    assert shutdown_run.status == PipelineRunState.SHUTDOWN
