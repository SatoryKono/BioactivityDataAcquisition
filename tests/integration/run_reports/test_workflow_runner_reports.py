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
"""Unit tests for workflow run report helpers."""

from __future__ import annotations

from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    _plan_steps_from_config,
    attach_workflow_run_report,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)


pytestmark = pytest.mark.integration


def test_plan_steps_from_config_reads_typed_step_fields() -> None:
    config = WorkflowConfig(
        name="wf",
        steps=(
            WorkflowStepConfig(step_id="p1", pipeline_name="chembl_activity"),
            TransformStepConfig(
                step_id="t1",
                transform_name="normalize",
                depends_on=("p1",),
            ),
        ),
    )

    plan = _plan_steps_from_config(config)

    assert plan == [
        {
            "step_id": "p1",
            "kind": "pipeline",
            "pipeline_name": "chembl_activity",
            "transform_name": None,
            "depends_on": [],
        },
        {
            "step_id": "t1",
            "kind": "transform",
            "pipeline_name": None,
            "transform_name": "normalize",
            "depends_on": ["p1"],
        },
    ]


def test_attach_workflow_run_report_logs_warning_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = MagicMock()
    result = WorkflowRunExecutionResult(
        workflow_name="wf",
        status="success",
        steps=(),
        workflow_run_id="run-1",
        manifest_id="manifest-1",
        execution_fingerprint="fp",
        resumed=False,
    )
    config = WorkflowConfig(
        name="wf",
        steps=(WorkflowStepConfig(step_id="p1", pipeline_name="chembl_activity"),),
    )
    monkeypatch.setattr(
        "bioetl.domain.run_reports.workflow_builder.build_workflow_run_report",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("report boom")),
    )

    degraded = attach_workflow_run_report(
        config=config, result=result, logger=logger, store=FileRunReportStoreAdapter()
    )

    assert degraded.run_report_error == "RuntimeError: report boom"
    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs["error_type"] == "RuntimeError"


def test_attach_workflow_run_report_records_completed_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _capture_build(**kwargs: object) -> object:
        captured["identity"] = kwargs["identity"]
        raise RuntimeError("stop after identity capture")

    logger = MagicMock()
    result = WorkflowRunExecutionResult(
        workflow_name="wf",
        status="success",
        steps=(),
        workflow_run_id="run-1",
        manifest_id="manifest-1",
        execution_fingerprint="fp",
        resumed=False,
    )
    config = WorkflowConfig(
        name="wf",
        steps=(WorkflowStepConfig(step_id="p1", pipeline_name="chembl_activity"),),
    )
    monkeypatch.setattr(
        "bioetl.domain.run_reports.workflow_builder.build_workflow_run_report",
        _capture_build,
    )

    attach_workflow_run_report(
        config=config, result=result, logger=logger, store=FileRunReportStoreAdapter()
    )

    identity = captured["identity"]
    assert isinstance(identity, dict)
    completed_at = identity.get("completed_at")
    assert isinstance(completed_at, str) and completed_at
    assert "T" in completed_at


def test_report_unwraps_real_transform_execution_result() -> None:
    from bioetl.application.services.workflow.workflow_runner_models import (
        WorkflowStepExecutionResult,
    )
    from bioetl.application.services.workflow.workflow_transform_service import (
        WorkflowTransformExecutionResult,
    )
    from bioetl.application.services.workflow.workflow_runner_reports import (
        _execution_rows_from_result,
    )
    from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report

    transform = WorkflowTransformExecutionResult(
        step_id="reconcile",
        transform_name="reconcile_foreign_keys",
        status="success",
        fingerprint="fp",
        output={
            "transform_name": "reconcile_foreign_keys",
            "source_table": "chembl.assay",
            "source_layer": "gold",
            "source_scope": "all_current",
            "mutation_mode": "gold_scd2_expiry",
            "orphan_rows_deleted": 1,
            "retained_rows": 5,
            "source_snapshot": {"version": 1, "physical_rows": 6, "current_rows": 5},
        },
    )
    result = WorkflowRunExecutionResult(
        workflow_name="wf",
        status="success",
        steps=(
            WorkflowStepExecutionResult(
                step_id="reconcile",
                step_kind="transform",
                status="success",
                payload=transform,
            ),
        ),
    )
    rows = _execution_rows_from_result(
        result, plan_steps=[], store=FileRunReportStoreAdapter()
    )
    report = build_workflow_run_report(
        identity={"workflow_name": "wf", "status": "success"},
        plan_steps=[],
        execution_steps=rows,
    )
    assert report.totals["gold_current_after_reconciliation_by_table"] == {
        "chembl.assay": 5
    }
    assert report.execution[0].reconciliation["source_snapshot"]["version"] == 1
