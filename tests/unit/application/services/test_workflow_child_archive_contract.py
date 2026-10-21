"""One child archive failure must not suppress later completed child archives."""

from unittest.mock import Mock

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    archive_workflow_children,
)
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig

pytestmark = pytest.mark.unit


def test_archive_continues_after_one_child_failure_and_ignores_non_pipeline_payload():
    config = WorkflowConfig(
        name="workflow",
        steps=(
            WorkflowStepConfig("first", "chembl_assay"),
            WorkflowStepConfig("second", "chembl_activity"),
        ),
    )
    first = RunResult(PipelineRunResult.SUCCESS, "chembl_assay", "run1", "backfill")
    second = RunResult(PipelineRunResult.SUCCESS, "chembl_activity", "run2", "backfill")
    result = WorkflowRunExecutionResult(
        "workflow",
        "success",
        (
            WorkflowStepExecutionResult("transform", "transform", "success", {}),
            WorkflowStepExecutionResult("first", "pipeline", "success", first),
            WorkflowStepExecutionResult("second", "pipeline", "success", second),
        ),
    )
    archive = Mock(side_effect=[OSError("first archive unavailable"), None])
    archive_workflow_children(config, result, archive)
    assert [call.args[0] for call in archive.call_args_list] == [first, second]
    assert all(call.args[1] is not None for call in archive.call_args_list)
