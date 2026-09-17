"""Unit coverage for forensic/inspection/query/workflow report modules <75%."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.forensic import (
    ForensicRunDiffResult,
    ForensicRunDiffService,
)
from bioetl.application.services.control_plane.manifest.inspection_artifact_refs import (
    build_artifact_ref_semantic_diff,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestDiffResult,
)
from bioetl.application.services.run_reports.query import (
    diff_pipeline_reports,
    list_pipeline_reports,
    list_workflow_reports,
    load_latest_pointer,
    load_pipeline_report,
    load_workflow_report,
    prune_reports,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_reports import (
    _execution_rows_from_result,
    _load_child_report_slice,
    _pipeline_name_for_step,
    _plan_steps_from_config,
    _require_workflow_result,
    attach_workflow_run_report,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)

pytestmark = pytest.mark.unit


def _file_run_report_store() -> object:
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    return FileRunReportStoreAdapter()


def test_forensic_diff_to_dict_and_compare_scopes() -> None:
    diff = RunManifestDiffResult(
        left_manifest_id="left",
        right_manifest_id="right",
        differences=(),
        classification="identical",
        semantic_difference_fields=("semantic",),
        occurrence_difference_fields=("occ",),
        noncanonical_difference_fields=("nc",),
    )
    payload = ForensicRunDiffResult(
        left_manifest_id="left",
        right_manifest_id="right",
        manifest_diff=diff,
        forensic_diff={"verdict": "ok"},
        missing_evidence={"left": ("a",), "right": ()},
    ).to_dict()
    assert payload["semantic_difference_fields"] == ["semantic"]
    assert payload["missing_evidence"] == {"left": ["a"], "right": []}

    left_show = SimpleNamespace(
        manifest=SimpleNamespace(manifest_id="left", run_id="run-left"),
        diagnostics={"artifact_refs": [{"artifact_id": "a"}]},
        ledger_entries=(),
    )
    right_show = SimpleNamespace(
        manifest=SimpleNamespace(manifest_id="right", run_id="run-right"),
        diagnostics={"artifact_refs": [{"artifact_id": "b"}]},
        ledger_entries=(),
    )
    inspection = SimpleNamespace(
        show=lambda identifier: left_show if identifier == "left" else right_show,
        diff=lambda *_args: diff,
    )
    no_port = ForensicRunDiffService(
        manifest_port=MagicMock(),
        inspection_service_factory=lambda: inspection,
    ).compare("left", "right")
    assert (
        no_port.artifact_byte_equivalence["comparison_scope"] == "unavailable_no_port"
    )

    empty_show = SimpleNamespace(
        manifest=SimpleNamespace(manifest_id="left", run_id="run-left"),
        diagnostics={},
        ledger_entries=(),
    )
    empty_inspection = SimpleNamespace(
        show=lambda _identifier: empty_show,
        diff=lambda *_args: diff,
    )
    missing = ForensicRunDiffService(
        manifest_port=MagicMock(),
        inspection_service_factory=lambda: empty_inspection,
        artifact_byte_comparison_port=MagicMock(),
    ).compare("left", "right")
    assert missing.artifact_byte_equivalence["comparison_scope"] == (
        "unavailable_missing_refs"
    )

    port = MagicMock()
    port.compare_artifacts.return_value = {"available": True, "equivalent": True}
    refs_inspection = SimpleNamespace(
        show=lambda _identifier: left_show,
        diff=lambda *_args: diff,
    )
    compared = ForensicRunDiffService(
        manifest_port=MagicMock(),
        inspection_service_factory=lambda: refs_inspection,
        artifact_byte_comparison_port=port,
    ).compare("left", "right")
    assert compared.artifact_byte_equivalence["equivalent"] is True


def test_artifact_ref_semantic_diff_branches() -> None:
    left = (
        {"artifact_id": "a", "stage": "gold", "run_id": "r1", "manifest_id": "m1"},
        {"artifact_id": "b", "stage": "silver", "run_id": "r1"},
    )
    occurrence = build_artifact_ref_semantic_diff(
        left_artifact_refs=left,
        right_artifact_refs=(
            {"artifact_id": "a", "stage": "gold", "run_id": "r2", "manifest_id": "m2"},
            {"artifact_id": "b", "stage": "silver", "run_id": "r2"},
        ),
    )
    assert occurrence["artifact_ref_semantic_equivalent"] is True
    assert occurrence["artifact_ref_occurrence_only"] is True

    semantic = build_artifact_ref_semantic_diff(
        left_artifact_refs=left,
        right_artifact_refs=({"artifact_id": "a", "stage": "bronze", "run_id": "r1"},),
    )
    assert semantic["artifact_ref_semantic_equivalent"] is False
    assert "artifact_ref_count" in semantic["artifact_ref_semantic_difference_fields"]


def test_run_report_query_load_list_diff_prune(tmp_path: Path) -> None:
    store = _file_run_report_store()
    assert load_latest_pointer(kind="pipeline", owner="missing", store=store) is None

    bad_pointer = tmp_path / "pipeline" / "broken" / "_latest.json"
    bad_pointer.parent.mkdir(parents=True)
    bad_pointer.write_text("{", encoding="utf-8")
    assert (
        load_latest_pointer(kind="pipeline", owner="broken", root=tmp_path, store=store)
        is None
    )

    run_dir = tmp_path / "pipeline" / "chembl_assay" / "run-1"
    run_dir.mkdir(parents=True)
    report = run_dir / "pipeline-run-report.json"
    report.write_text(
        json.dumps(
            {
                "identity": {
                    "run_id": "run-1",
                    "pipeline_name": "chembl_assay",
                    "status": "success",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pipeline" / "chembl_assay" / "_latest.json").write_text(
        json.dumps({"json_path": str(report)}), encoding="utf-8"
    )
    (run_dir / "pipeline-run-report.md").write_text("ok", encoding="utf-8")
    assert load_pipeline_report(
        pipeline_name="chembl_assay", run_id="run-1", root=tmp_path, store=store
    )
    assert load_pipeline_report(
        pipeline_name="chembl_assay", latest=True, root=tmp_path, store=store
    )
    listed = list_pipeline_reports(
        pipeline_name="chembl_assay", root=tmp_path, store=store
    )
    assert listed[0].markdown_path is not None

    wf_dir = tmp_path / "workflow" / "nightly" / "wf-1"
    wf_dir.mkdir(parents=True)
    wf_report = wf_dir / "workflow-run-report.json"
    wf_report.write_text(
        json.dumps({"identity": {"status": "success"}}), encoding="utf-8"
    )
    (tmp_path / "workflow" / "nightly" / "_latest.json").write_text(
        json.dumps({"json_path": str(wf_report)}), encoding="utf-8"
    )
    assert load_workflow_report(
        workflow_name="nightly", workflow_run_id="wf-1", root=tmp_path, store=store
    )
    assert load_workflow_report(
        workflow_name="nightly", latest=True, root=tmp_path, store=store
    )
    assert list_workflow_reports(root=tmp_path, store=store)

    left = {
        "identity": {"run_id": "l"},
        "funnel": [{"stage_id": "extract", "records_in": 2, "records_out": 2}],
        "reasons_top_n": [{"reason_code": "dq", "count": 1}],
    }
    right = {
        "identity": {"run_id": "r"},
        "funnel": [{"stage_id": "extract", "records_in": 5, "records_out": "3"}],
        "reasons_top_n": [{"reason_code": "dq", "count": "2"}],
    }
    delta = diff_pipeline_reports(left, right)
    assert delta["funnel_delta"][0]["records_in_delta"] == 3
    with pytest.raises(TypeError):
        diff_pipeline_reports([], right)
    with pytest.raises(ValueError, match="kind must"):
        prune_reports(kind="other", store=store, max_count=1)
    with pytest.raises(ValueError, match="provide max_count"):
        prune_reports(kind="pipeline", store=store)
    with pytest.raises(ValueError, match="now is required"):
        prune_reports(kind="pipeline", store=store, max_age_days=1)
    assert prune_reports(
        kind="pipeline",
        owner="chembl_assay",
        max_count=0,
        root=tmp_path,
        dry_run=False,
        store=store,
    )
    assert prune_reports(
        kind="workflow",
        owner="nightly",
        max_age_days=0,
        now=datetime(2099, 1, 1, tzinfo=UTC),
        root=tmp_path,
        dry_run=True,
        store=store,
    )


def test_list_reports_skips_unreadable_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _file_run_report_store()
    run_dir = tmp_path / "pipeline" / "chembl_assay" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "pipeline-run-report.json").write_text("{}", encoding="utf-8")
    real_mtime = store.mtime

    def _mtime(path: str) -> float:
        if path.endswith("pipeline-run-report.json"):
            raise OSError("locked")
        return real_mtime(path)

    monkeypatch.setattr(store, "mtime", _mtime)
    assert list_pipeline_reports(root=tmp_path, store=store) == []


def test_workflow_runner_reports_helpers(tmp_path: Path) -> None:
    config = WorkflowConfig(
        name="wf",
        steps=(
            WorkflowStepConfig(step_id="p1", pipeline_name="chembl_activity"),
            TransformStepConfig(
                step_id="t1", transform_name="normalize", depends_on=("p1",)
            ),
        ),
    )
    plan = _plan_steps_from_config(config)
    assert plan[0]["kind"] == "pipeline"
    assert plan[1]["kind"] == "transform"
    with pytest.raises(TypeError):
        _require_workflow_result(object())

    store = _file_run_report_store()
    assert _load_child_report_slice(None, store=store) == ((), None)
    assert _load_child_report_slice(str(tmp_path / "missing.json"), store=store) == (
        (),
        None,
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert _load_child_report_slice(str(bad), store=store) == ((), None)
    listed = tmp_path / "list.json"
    listed.write_text("[]", encoding="utf-8")
    assert _load_child_report_slice(str(listed), store=store) == ((), None)
    child = tmp_path / "child.json"
    child.write_text(
        json.dumps(
            {
                "reasons_top_n": [{"reason_code": "dq", "count": 1}],
                "layers": {"gold_excluded_by_contract": 4},
            }
        ),
        encoding="utf-8",
    )
    _reasons, excluded = _load_child_report_slice(str(child), store=store)
    assert excluded == 4

    payload = SimpleNamespace(pipeline_name="from-payload")
    named = WorkflowStepExecutionResult(
        step_id="p1", step_kind="pipeline", status="success", payload=payload
    )
    assert _pipeline_name_for_step(named, plan_steps=plan, payload=payload) == (
        "from-payload"
    )
    unnamed = WorkflowStepExecutionResult(
        step_id="p1", step_kind="pipeline", status="success", payload=None
    )
    assert _pipeline_name_for_step(unnamed, plan_steps=plan, payload=None) == (
        "chembl_activity"
    )
    unknown = WorkflowStepExecutionResult(
        step_id="missing", step_kind="pipeline", status="success"
    )
    assert _pipeline_name_for_step(unknown, plan_steps=plan, payload=None) is None

    result = WorkflowRunExecutionResult(
        workflow_name="wf",
        status="success",
        steps=(
            WorkflowStepExecutionResult(
                step_id="p1",
                step_kind="pipeline",
                status="success",
                payload=SimpleNamespace(run_report_json_path=str(child)),
            ),
            WorkflowStepExecutionResult(
                step_id="t1",
                step_kind="transform",
                status="success",
                payload=SimpleNamespace(
                    output=SimpleNamespace(run_report_json_path=str(child))
                ),
            ),
        ),
        workflow_run_id=str(UUID("00000000-0000-4000-8000-000000000001")),
        started_at="2026-01-01T00:00:00+00:00",
        duration_seconds=1.0,
    )
    rows = _execution_rows_from_result(result, plan_steps=plan, store=store)
    assert rows[0]["gold_excluded_by_contract"] == 4
    attached = attach_workflow_run_report(
        config=config,
        result=result,
        store=store,
        report_root=tmp_path / "reports",
    )
    assert attached.run_report_json_path is not None
    logger = MagicMock()
    failed = attach_workflow_run_report(
        config=config,
        result=result,
        logger=logger,
        store=MagicMock(
            is_file=lambda _path: False,
            write_text=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("write failed")
            ),
            mkdir=lambda *_args, **_kwargs: None,
        ),
        report_root=tmp_path / "reports-fail",
    )
    assert failed.run_report_error is not None
    logger.warning.assert_called()
