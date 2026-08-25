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
"""Unit tests for workflow execution recording helpers."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.workflow.control_plane import execution_recording
from bioetl.application.services.workflow.control_plane.execution_recording import (
    WorkflowExecutionRecorder,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformDestructiveCommit,
    WorkflowTransformExecutionResult,
)
from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.types import RunID
from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig

pytestmark = pytest.mark.unit


def _make_state() -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000301")),
        manifest_id="manifest-1",
        workflow_name="chembl_baseline",
        execution_fingerprint="fingerprint-1",
        status="pending",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        completed_at=None,
        selected_step_ids=("extract", "reconcile"),
        steps=(),
        completed_transform_fingerprints={},
    )


def _make_context() -> tuple[WorkflowExecutionRecorder, list[WorkflowExecutionState]]:
    saved: list[WorkflowExecutionState] = []
    ledger = SimpleNamespace(
        record_repair_requested=lambda step_ids: None,
        record_force_requested=lambda step_ids: None,
        record_workflow_started=lambda resumed: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
            entry_id="started-1",
        ),
        record_step_started=lambda step_id, step_kind, details: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=UTC),
            entry_id=f"start-{step_id}",
        ),
        record_step_completed=lambda **kwargs: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 3, tzinfo=UTC),
            entry_id=f"done-{kwargs['step_id']}",
        ),
        record_step_commit_pending_confirmation=lambda **kwargs: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 4, tzinfo=UTC),
            entry_id=f"pending-{kwargs['step_id']}",
        ),
        record_workflow_finished=lambda details: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
            entry_id="finished-1",
        ),
        record_workflow_failed=lambda **kwargs: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
            entry_id="failed-1",
        ),
    )
    context = WorkflowExecutionRecorder(
        ledger=ledger,
        state_port=SimpleNamespace(save=lambda state: saved.append(state)),
        state=_make_state(),
    )
    return context, saved


def test_record_workflow_started_updates_running_state_and_clears_repairs() -> None:
    context, saved = _make_context()
    context.state = replace(
        context.state,
        ambiguous_step_ids=("extract", "reconcile"),
        repair_required=True,
        repair_hint="needs repair",
    )

    execution_recording.record_workflow_started(
        context,
        resumed=True,
        repair_steps=("extract",),
        force_steps=("reconcile",),
    )

    assert context.state.status == "running"
    assert context.state.repair_required is False
    assert context.state.last_event_id == "started-1"
    assert saved


def test_record_workflow_started_skips_optional_repair_force_paths() -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []

    ledger = SimpleNamespace(
        record_repair_requested=lambda step_ids: calls.append(("repair", step_ids)),
        record_force_requested=lambda step_ids: calls.append(("force", step_ids)),
        record_workflow_started=lambda resumed: SimpleNamespace(
            occurred_at=datetime(2026, 1, 1, 12, 1, tzinfo=UTC),
            entry_id="started-2",
        ),
    )
    context = WorkflowExecutionRecorder(
        ledger=ledger,
        state_port=SimpleNamespace(save=lambda state: None),
        state=_make_state(),
    )

    execution_recording.record_workflow_started(
        context,
        resumed=False,
        repair_steps=(),
        force_steps=(),
    )

    assert calls == []
    assert context.state.status == "running"
    assert context.state.last_event_id == "started-2"


def test_record_step_started_completed_and_transform_commit_update_state() -> None:
    context, saved = _make_context()

    execution_recording.record_step_started(
        context,
        WorkflowStepConfig(step_id="extract", pipeline_name="chembl_activity"),
    )
    assert context.state.steps[0].status == "running"

    execution_recording.record_step_completed(
        context,
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status="success",
        ),
    )
    assert context.state.steps[0].status == "success"

    execution_recording.record_transform_commit(
        context,
        WorkflowTransformDestructiveCommit(
            step_id="reconcile",
            transform_name="reconcile_foreign_keys",
            fingerprint="fp-1",
            details={"mutated": True},
        ),
    )
    assert context.state.repair_required is True
    assert "reconcile" in context.state.ambiguous_step_ids
    assert saved


def test_record_step_started_uses_transform_kind_and_fingerprint_details() -> None:
    captured: list[dict[str, object]] = []

    ledger = SimpleNamespace(
        record_step_started=lambda step_id, step_kind, details: (
            captured.append(
                {
                    "step_id": step_id,
                    "step_kind": step_kind,
                    "details": details,
                }
            )
            or SimpleNamespace(
                occurred_at=datetime(2026, 1, 1, 12, 2, tzinfo=UTC),
                entry_id="start-transform",
            )
        )
    )
    saved: list[WorkflowExecutionState] = []
    context = WorkflowExecutionRecorder(
        ledger=ledger,
        state_port=SimpleNamespace(save=lambda state: saved.append(state)),
        state=_make_state(),
    )

    execution_recording.record_step_started(
        context,
        TransformStepConfig(
            step_id="reconcile",
            transform_name="reconcile_foreign_keys",
        ),
        fingerprint="fp-transform",
    )

    assert captured == [
        {
            "step_id": "reconcile",
            "step_kind": "transform",
            "details": {"fingerprint": "fp-transform"},
        }
    ]
    assert saved[-1].steps[0].fingerprint == "fp-transform"


def test_record_step_completed_handles_resume_shortcut_without_replacing_state() -> (
    None
):
    context, saved = _make_context()

    execution_recording.record_step_completed(
        context,
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status="success",
            error_type="AlreadyCompletedOnResume",
            payload={"fingerprint": "resume-fp"},
        ),
    )

    assert context.state.steps == ()
    assert context.state.last_event_id == "done-extract"
    assert saved


def test_record_workflow_finished_covers_success_and_failure_outcomes() -> None:
    success_context, success_saved = _make_context()
    success_result = WorkflowRunExecutionResult(
        workflow_name="chembl_baseline",
        status="success",
        steps=(
            WorkflowStepExecutionResult(
                step_id="extract",
                step_kind="pipeline",
                status="success",
            ),
        ),
    )

    execution_recording.record_workflow_finished(
        success_context,
        success_result,
        completed_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
        last_start_offset=10,
        last_limit=20,
    )

    assert success_context.state.status == "success"
    assert success_context.state.last_limit == 20
    assert success_saved

    failure_context, failure_saved = _make_context()
    failure_result = WorkflowRunExecutionResult(
        workflow_name="chembl_baseline",
        status="failed",
        steps=(
            WorkflowStepExecutionResult(
                step_id="reconcile",
                step_kind="transform",
                status="failed",
                error_type="ValueError",
                error_message="bad data",
            ),
        ),
    )

    execution_recording.record_workflow_finished(
        failure_context,
        failure_result,
        completed_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
    )

    assert failure_context.state.status == "failed"
    assert failure_context.state.last_error_type == "ValueError"
    assert failure_saved


def test_recording_helpers_cover_transform_fingerprints_and_step_removal() -> None:
    state = _make_state()
    updated = execution_recording._record_completed_transform_fingerprint(
        state,
        step_id="reconcile",
        fingerprint="fp-1",
    )
    assert updated.completed_transform_fingerprints == {"reconcile": "fp-1"}

    ambiguous = replace(
        state,
        ambiguous_step_ids=("extract", "reconcile"),
        repair_required=True,
        repair_hint="needs repair",
    )
    cleared = execution_recording._clear_ambiguous_step(ambiguous, "extract")
    assert cleared.ambiguous_step_ids == ("reconcile",)
    assert cleared.repair_required is True

    fully_cleared = execution_recording._clear_ambiguous_step(ambiguous, "missing")
    assert fully_cleared.repair_hint == "needs repair"


def test_internal_recording_helpers_cover_none_and_fallback_paths() -> None:
    state = _make_state()

    assert (
        execution_recording._record_completed_transform_fingerprint(
            state,
            step_id="extract",
            fingerprint=None,
        )
        is state
    )
    assert execution_recording._fingerprint_details(None) is None
    assert execution_recording._fingerprint_details("fp") == {"fingerprint": "fp"}
    assert (
        execution_recording._resolve_result_fingerprint(
            WorkflowStepExecutionResult(
                step_id="extract",
                step_kind="pipeline",
                status="success",
                payload=SimpleNamespace(fingerprint="attr-fp"),
            )
        )
        == "attr-fp"
    )
    assert (
        execution_recording._resolve_result_fingerprint(
            WorkflowStepExecutionResult(
                step_id="extract",
                step_kind="pipeline",
                status="success",
                payload={"fingerprint": "dict-fp"},
            )
        )
        == "dict-fp"
    )
    assert (
        execution_recording._resolve_result_fingerprint(
            WorkflowStepExecutionResult(
                step_id="extract",
                step_kind="pipeline",
                status="success",
                payload={"missing": True},
            )
        )
        is None
    )
    assert execution_recording._find_step_state(state, "missing") is None

    summary = execution_recording._build_result_summary(
        WorkflowRunExecutionResult(
            workflow_name="chembl_baseline",
            status="failed",
            steps=(
                WorkflowStepExecutionResult(
                    step_id="extract",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="reconcile",
                    step_kind="transform",
                    status="skipped",
                ),
            ),
        )
    )
    assert summary == {
        "status": "failed",
        "step_counts": {"success": 1, "failed": 0, "skipped": 1},
    }
    assert (
        execution_recording._find_failed_step(
            WorkflowRunExecutionResult(
                workflow_name="chembl_baseline",
                status="success",
                steps=(),
            )
        )
        is None
    )
    assert execution_recording._workflow_failure_message(None) == (
        "Workflow execution failed"
    )


def test_step_completion_details_include_transform_summary_and_artifact_refs() -> None:
    details = execution_recording.build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="reconcile",
            step_kind="transform",
            status="success",
            payload=WorkflowTransformExecutionResult(
                step_id="reconcile",
                transform_name="reconcile_foreign_keys",
                status="success",
                fingerprint="fp",
                output={
                    "fingerprint": "fp",
                    "transform_name": "reconcile_foreign_keys",
                    "source_table": "chembl.assay",
                    "reference_table": "chembl.target",
                    "scanned_rows": 3,
                    "retained_rows": 2,
                    "orphan_rows_deleted": 1,
                    "artifact_refs": [
                        {
                            "type": "workflow_transform_result",
                            "path": "result.json",
                            "sha256": "abc",
                            "size_bytes": 10,
                        }
                    ],
                },
            ),
        )
    )

    assert details is not None
    assert details["fingerprint"] == "fp"
    summary = details["transform_result_summary"]
    assert isinstance(summary, dict)
    assert summary["source_table"] == "chembl.assay"
    assert summary["orphan_rows_deleted"] == 1
    assert details["artifacts"] == [
        {
            "type": "workflow_transform_result",
            "path": "result.json",
            "sha256": "abc",
            "size_bytes": 10,
        }
    ]


@pytest.mark.parametrize("status", ["success", "failed"])
def test_pipeline_step_completion_details_include_child_run_anchors(
    status: str,
) -> None:
    details = execution_recording.build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status=status,
            payload=SimpleNamespace(
                run_id=UUID("00000000-0000-0000-0000-000000000411"),
                manifest_id="manifest-child-411",
            ),
        )
    )

    assert details == {
        "child_run_id": "00000000-0000-0000-0000-000000000411",
        "child_manifest_id": "manifest-child-411",
    }


def test_failed_pipeline_completion_uses_exception_safe_child_anchors() -> None:
    details = execution_recording.build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="extract",
            step_kind="pipeline",
            status="failed",
            error_type="RuntimeError",
            error_message="pipeline boom",
            child_run_id="00000000-0000-0000-0000-000000000419",
            child_manifest_id="manifest-child-419",
        )
    )

    assert details == {
        "child_run_id": "00000000-0000-0000-0000-000000000419",
        "child_manifest_id": "manifest-child-419",
    }
