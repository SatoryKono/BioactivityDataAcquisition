"""Pending mutations and restored outputs retain their durable workflow binding."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.services.workflow.control_plane import (
    execution_recording_state as recording,
)
from bioetl.application.services.workflow.control_plane import (
    execution_service as execution,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    build_reconcile_foreign_keys_executor,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from tests.unit.application.workflow.transforms.test_issue_10518_reconcile_fk_residuals import (
    _spec,
)

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 21, tzinfo=UTC)


def test_failed_pending_commit_keeps_repair_required_state():
    pending = WorkflowStepState(
        "mutate",
        "transform",
        "running",
        destructive=True,
        commit_pending_confirmation=True,
    )
    state = WorkflowExecutionState(
        "run",
        "manifest",
        "workflow",
        "fingerprint",
        "running",
        NOW,
        NOW,
        None,
        ("mutate",),
        (pending,),
        {},
        repair_required=True,
        ambiguous_step_ids=("mutate",),
    )
    result = WorkflowStepExecutionResult(
        "mutate",
        "transform",
        "failed",
        error_type="OSError",
        error_message="commit uncertain",
    )
    updated = recording._apply_completed_step_state(
        state,
        result=result,
        fingerprint="fingerprint",
        updated_at=NOW,
        last_event_id="event",
    )
    assert updated.repair_required and updated.ambiguous_step_ids == ("mutate",)
    assert updated.steps[0].commit_pending_confirmation
    assert updated.last_error_message == "commit uncertain"


@pytest.mark.asyncio
async def test_locked_resume_passes_restored_outputs_to_runner(monkeypatch):
    saved = {"extract": {"run_id": "saved-run"}}
    monkeypatch.setattr(
        execution, "restore_selected_snapshot_outputs", lambda *args: saved
    )
    monkeypatch.setattr(execution, "record_workflow_started", Mock())
    finished = Mock()
    monkeypatch.setattr(execution, "record_workflow_finished", finished)
    recorder = SimpleNamespace(state=object())
    runner = SimpleNamespace(
        run_workflow=AsyncMock(
            return_value=WorkflowRunExecutionResult("workflow", "success", ())
        )
    )
    manifest = SimpleNamespace(
        workflow_run_id="run",
        manifest_id="manifest",
        execution_fingerprint="fingerprint",
    )
    config = WorkflowConfig(
        "workflow", (WorkflowStepConfig("extract", "chembl_assay"),)
    )
    result = await execution._run_locked_workflow(
        runner=runner,
        recorder=recorder,
        prepared_manifest=manifest,
        completed_step_ids=frozenset({"extract"}),
        completed_transform_fingerprints={},
        config=config,
        resumed=True,
        repair_steps=(),
        force_steps=(),
        now_factory=lambda: NOW,
    )
    assert runner.run_workflow.await_args.kwargs["restored_step_outputs"] is saved
    assert result.resumed and result.manifest_id == "manifest"
    finished.assert_called_once()


@pytest.mark.asyncio
async def test_ambiguous_selected_snapshot_commit_cannot_return_success():
    from bioetl.domain.workflow.foreign_key_reconciliation_models import (
        ForeignKeyReconciliationResult,
    )

    result = ForeignKeyReconciliationResult(
        "chembl_assay",
        "chembl_target",
        "target_id",
        "target_id",
        "delete_orphans",
        1,
        1,
        0,
        False,
        mutation_blocked_reason="selected_snapshot_commit_ambiguous",
    )
    port = SimpleNamespace(reconcile_foreign_keys=AsyncMock(return_value=result))
    with pytest.raises(RuntimeError, match="ambiguous; repair required"):
        await build_reconcile_foreign_keys_executor(port)(_spec(), {})
