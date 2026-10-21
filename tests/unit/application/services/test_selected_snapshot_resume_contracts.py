"""Resume consumes saved producer evidence and never captures a replacement run."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.services.execution import (
    workflow_runner_step_execution as execution,
)
from bioetl.application.services.workflow.control_plane import (
    selected_snapshot_resume as resume,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunnerService,
)
from bioetl.domain.control_plane import WorkflowStepState
from bioetl.domain.workflow.config import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)
from bioetl.domain.workflow._run_options_config import WorkflowRunOptionsConfig

pytestmark = pytest.mark.unit


def _receipt():
    return {
        "schema_version": 1,
        "pipeline_name": "chembl_assay",
        "run_id": "run",
        "manifest_id": "manifest",
        "run_type": "incremental",
        "status": "success",
        "started_at": "2026-10-21T00:00:00+00:00",
        "completed_at": "2026-10-21T00:00:01+00:00",
        **dict.fromkeys(
            (
                "records_fetched",
                "records_bronze",
                "records_silver",
                "records_gold",
                "records_gold_excluded_by_contract",
                "records_quarantined",
                "records_filtered_out",
            ),
            1,
        ),
    }


def _details():
    return {
        "child_run_id": "run",
        "child_manifest_id": "manifest",
        "producer_result": _receipt(),
        "selected_snapshots": {
            "silver:chembl.assay": {
                "version": 1,
                "table_id": "table",
                "producer_pipeline": "chembl_assay",
                "run_ids": ["run"],
            }
        },
    }


def test_resume_rejects_a_producer_without_run_type():
    details = _details()
    details["producer_result"]["run_type"] = None
    with pytest.raises(ValueError, match="producer identity incomplete"):
        resume._restore_producer(WorkflowStepConfig("extract", "chembl_assay"), details)


@pytest.mark.parametrize("key", ["started_at", "completed_at"])
def test_resume_rejects_incomplete_producer_timestamps(key):
    details = _details()
    details["producer_result"][key] = "invalid"
    with pytest.raises(ValueError, match="producer timestamps incomplete"):
        resume._restore_producer(WorkflowStepConfig("extract", "chembl_assay"), details)


def test_completed_step_without_saved_evidence_cannot_be_replayed():
    config = WorkflowConfig(
        "workflow",
        (WorkflowStepConfig("extract", "chembl_assay"),),
        defaults=WorkflowRunOptionsConfig(reconciliation_mode="selected-snapshot"),
    )
    with pytest.raises(ValueError, match="lacks completed step evidence"):
        resume.restore_selected_snapshot_outputs(
            config, SimpleNamespace(steps=()), frozenset({"extract"})
        )


def test_resume_ignores_steps_that_were_not_completed():
    config = WorkflowConfig(
        "workflow",
        (WorkflowStepConfig("extract", "chembl_assay"),),
        defaults=WorkflowRunOptionsConfig(reconciliation_mode="selected-snapshot"),
    )
    state = SimpleNamespace(steps=(WorkflowStepState("extract", "pipeline", "failed"),))
    assert resume.restore_selected_snapshot_outputs(config, state, frozenset()) == {}


def test_transform_completion_preserves_its_saved_summary():
    step = WorkflowStepState(
        "derive",
        "transform",
        "success",
        output_details={"transform_result_summary": {"rows": 2}},
    )
    assert resume._completion_payload(step, step.output_details) == {"rows": 2}


@pytest.mark.parametrize(
    "status, definition, reason",
    [
        (
            "failed",
            WorkflowStepConfig("extract", "chembl_assay"),
            "producer was not successful",
        ),
        (
            "success",
            TransformStepConfig("extract", "derive"),
            "lacks producer evidence definition",
        ),
    ],
)
def test_invalid_completed_producer_cannot_be_restored(status, definition, reason):
    config = WorkflowConfig("workflow", (definition,))
    step = WorkflowStepState("extract", "pipeline", status)
    with pytest.raises(ValueError, match=reason):
        resume._restore_completed_step(config, step, {"extract"})


def test_reconciliation_completion_without_pins_cannot_use_latest_tables():
    definition = TransformStepConfig("reconcile", "reconcile_foreign_keys")
    with pytest.raises(ValueError, match="lacks producer evidence"):
        resume._restore_completed_step(
            WorkflowConfig("workflow", (definition,)),
            WorkflowStepState("reconcile", "transform", "success"),
            set(),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode, reason",
    [
        ("cohort", "reference_cohort resolver unavailable"),
        ("snapshot", "snapshot reader"),
    ],
)
async def test_required_execution_dependencies_fail_before_starting_pipeline(
    mode, reason
):
    from bioetl.domain.workflow.config import WorkflowReferenceCohort

    step = WorkflowStepConfig(
        "extract",
        "chembl_assay",
        reference_cohort=WorkflowReferenceCohort("producer", "chembl.assay", "id", "id")
        if mode == "cohort"
        else None,
    )
    runner = SimpleNamespace(run=AsyncMock())
    result = await execution.execute_pipeline_step(
        pipeline_runner=runner,
        metrics=Mock(),
        monotonic=lambda: 1.0,
        workflow_name="workflow",
        step=step,
        workflow_context_labels={},
        step_started_callback=None,
        workflow_run_id="workflow-run",
        capture_producer_snapshot=mode == "snapshot",
    )
    assert result.status == "failed" and reason in result.error_message
    runner.run.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_capture_without_reader_still_fails_closed():
    with pytest.raises(ValueError, match="snapshot reader"):
        await execution._capture_producer_result(
            SimpleNamespace(is_success=True),
            WorkflowStepConfig("extract", "chembl_assay"),
            None,
            True,
        )


@pytest.mark.asyncio
async def test_resume_skipped_child_retains_saved_identity_without_execution(
    monkeypatch,
):
    pipeline = SimpleNamespace(run=AsyncMock())
    service = WorkflowRunnerService(pipeline, Mock(), Mock(), Mock())
    monkeypatch.setattr(WorkflowRunnerService, "_finalize_run_result", Mock())
    config = WorkflowConfig(
        "workflow", (WorkflowStepConfig("extract", "chembl_assay"),)
    )
    callback = Mock()
    saved = {"run_id": "saved-run", "manifest_id": "saved-manifest"}
    await service.run_workflow(
        config,
        resumed=True,
        completed_step_ids=frozenset({"extract"}),
        restored_step_outputs={"extract": saved},
        step_completed_callback=callback,
        created_at_factory=lambda: datetime(2026, 10, 21, tzinfo=UTC),
    )
    result = callback.call_args.args[0]
    assert result.status == "skipped" and result.payload is saved
    assert (result.child_run_id, result.child_manifest_id) == (
        "saved-run",
        "saved-manifest",
    )
    pipeline.run.assert_not_awaited()
