"""Scoped FK UI evidence preserves exact counts and independent assessments."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import DOMAINS
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http._pipeline_run_report_table import (
    _table_shape_workflow_run_report,
)
from bioetl.interfaces.http._reconciliation_display import (
    linked_reconciliation_display,
    reconciliation_display,
)
from bioetl.interfaces.http.selected_run_status import load_selected_run_status

pytestmark = pytest.mark.unit


def test_explicit_standalone_is_not_applicable_without_mutating_report(tmp_path):
    report = {
        "identity": dict.fromkeys(
            ("workflow_id", "workflow_run_id", "workflow_step_id")
        )
    }
    original = copy.deepcopy(report)
    row = linked_reconciliation_display(report, tmp_path)[0]
    assert row["result"] == row["pins"] == row["limit"] == "N/A"
    assert "Standalone" in row["meaning"]
    assert report == original


@pytest.mark.parametrize(
    "identity", [{}, {"workflow_run_id": "parent"}, {"workflow_run_id": None}]
)
def test_absent_or_incomplete_binding_stays_unknown(tmp_path, identity):
    assert (
        linked_reconciliation_display({"identity": identity}, tmp_path)[0]["result"]
        == "UNKNOWN"
    )


def test_persisted_pipeline_only_plan_is_not_applicable():
    payload = {"plan": {"steps": [{"kind": "pipeline"}]}, "execution": []}
    assert reconciliation_display(payload)[0]["result"] == "N/A"
    payload["plan"]["steps"].append(
        {"kind": "transform", "transform_name": "reconcile_foreign_keys"}
    )
    assert reconciliation_display(payload)[0]["result"] == "UNKNOWN"


def _reconciliation(deleted=8, retained=2):
    return {
        "reconciliation_mode": "selected-snapshot",
        "source_scope": "current_run",
        "reference_scope": "current_run",
        "source_layer": "gold",
        "source_table": "chembl.assay",
        "reference_layer": "gold",
        "reference_table": "chembl.target",
        "reference_completeness": "unproven",
        "mutation_mode": "gold_scd2_expiry",
        "orphan_rows_deleted": deleted,
        "scanned_rows": 10,
        "retained_rows": retained,
        "input_snapshots": {
            "gold:chembl.assay": {
                "version": 1,
                "limit": 1000,
                "owned_entities": {"secret": "hash"},
            },
            "gold:chembl.target": {"version": 0, "limit": 1000},
        },
    }


def _parent(recon):
    return {
        "schema_version": "workflow_run_report_v1",
        "identity": {"workflow_name": "chembl_core", "workflow_run_id": "parent-a"},
        "execution": [
            {
                "step_id": "run_assay",
                "pipeline_name": "chembl_assay",
                "pipeline_run_id": "child-a",
            },
            {"step_id": "reconcile_assay_target", "reconciliation": recon},
        ],
    }


def _child():
    return {
        "identity": {"pipeline_name": "chembl_assay", "run_id": "child-a"},
        "observations": {
            "Workflow": {
                "facts": {
                    "identity": {
                        "workflow_name": "chembl_core",
                        "workflow_run_id": "parent-a",
                    },
                    "step_id": "run_assay",
                }
            }
        },
    }


def _write_parent(root: Path, parent):
    path = root / "workflow/chembl_core/parent-a/workflow-run-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(parent), encoding="utf-8")
    return path


@pytest.mark.parametrize("deleted,retained", [(8, 2), (10, 0), (0, 10)])
def test_partial_total_and_zero_expiry_use_persisted_denominator(deleted, retained):
    payload = _parent(_reconciliation(deleted, retained))
    before = copy.deepcopy(payload)
    row = _table_shape_workflow_run_report(payload)["reconciliation_display"][0]
    assert row["result"] == f"expired {deleted}/10; retained {retained}"
    assert row["mode"] == "selected-snapshot"
    assert row["scope"] == "current_run → current_run"
    assert row["pins"] == "gold:chembl.assay@1 → gold:chembl.target@0"
    assert row["limit"] == "source 1000; reference 1000"
    assert (
        row["meaning"]
        == "Orphan = no match in selected reference; completeness: unproven"
    )
    assert "secret" not in json.dumps(row)
    assert payload == before


@pytest.mark.parametrize("mode", [None, "unsupported", []])
def test_old_or_unknown_mode_never_infers_complete_reference(mode):
    recon = _reconciliation()
    recon["reconciliation_mode"] = mode
    row = reconciliation_display(_parent(recon))[0]
    assert row["mode"] == "Not recorded"
    assert row["result"] == "UNKNOWN"


def test_missing_counts_and_pins_never_infer_zero():
    recon = _reconciliation()
    for key in ("input_snapshots", "scanned_rows", "retained_rows"):
        recon.pop(key)
    recon["orphan_rows_deleted"] = False
    row = reconciliation_display(_parent(recon))[0]
    assert row["result"] == "expired UNKNOWN/UNKNOWN; retained UNKNOWN"
    assert row["pins"] == "gold:chembl.assay@UNKNOWN → gold:chembl.target@UNKNOWN"


def test_missing_or_null_scope_is_unknown():
    recon = _reconciliation()
    recon.pop("source_scope")
    recon["reference_scope"] = None
    assert reconciliation_display(_parent(recon))[0]["scope"] == "UNKNOWN → UNKNOWN"


def test_dry_run_never_claims_actual_expiry():
    recon = _reconciliation(0, 10)
    recon["dry_run"] = True
    assert (
        reconciliation_display(_parent(recon))[0]["result"]
        == "dry run; removed 0/10; retained 10"
    )


def test_exact_parent_binding_exposes_all_parent_transforms(tmp_path):
    parent = _parent(_reconciliation())
    parent["execution"].append(
        {
            "step_id": "reconcile_publication_assay",
            "reconciliation": _reconciliation(10, 0),
        }
    )
    _write_parent(tmp_path, parent)
    rows = linked_reconciliation_display(_child(), tmp_path)
    assert len(rows) == 2
    assert rows[1]["result"] == "expired 10/10; retained 0"


@pytest.mark.parametrize(
    "field,value",
    [
        ("pipeline_run_id", "foreign"),
        ("pipeline_name", "foreign"),
        ("step_id", "foreign"),
    ],
)
def test_parent_child_mismatch_never_exposes_foreign_reconciliation(
    tmp_path, field, value
):
    parent = _parent(_reconciliation())
    parent["execution"][0][field] = value
    _write_parent(tmp_path, parent)
    row = linked_reconciliation_display(_child(), tmp_path)[0]
    assert row["result"] == "UNKNOWN"
    assert row["meaning"] == "Parent workflow child binding mismatch"


def test_missing_corrupt_or_identity_mismatched_parent_is_explicit(tmp_path):
    assert (
        linked_reconciliation_display(_child(), tmp_path)[0]["meaning"]
        == "Parent workflow report missing"
    )
    path = _write_parent(tmp_path, _parent(_reconciliation()))
    path.write_text("{broken", encoding="utf-8")
    assert "corrupt" in linked_reconciliation_display(_child(), tmp_path)[0]["meaning"]
    parent = _parent(_reconciliation())
    parent["identity"]["workflow_run_id"] = "foreign"
    _write_parent(tmp_path, parent)
    assert (
        "identity mismatch"
        in linked_reconciliation_display(_child(), tmp_path)[0]["meaning"]
    )


def test_projection_does_not_promote_saved_assessment_or_mutate_report(tmp_path):
    child = _child()
    draft = build_pipeline_run_report(
        identity={**child["identity"], "status": "success"}, metrics={}
    )
    draft = replace(
        draft,
        observations={
            **{
                name: {"verdict": "OK", "reason": "checked", "facts": {}}
                for name in DOMAINS[1:]
            },
            **child["observations"],
        },
    )
    write_pipeline_run_report(draft, root=tmp_path, store=FileRunReportStoreAdapter())
    path = tmp_path / "pipeline/chembl_assay/child-a/pipeline-run-report.json"
    original = path.read_bytes()
    absent = load_selected_run_status(
        pipeline="chembl_assay", run_id="child-a", root=tmp_path
    )
    _write_parent(tmp_path, _parent(_reconciliation(10, 0)))
    present = load_selected_run_status(
        pipeline="chembl_assay", run_id="child-a", root=tmp_path
    )
    assert present["reconciliation_display"][0]["result"] == "expired 10/10; retained 0"
    for field in (
        "verdict",
        "revision",
        "evidence_completeness",
        "replay_readiness_now",
        "domains",
    ):
        assert present[field] == absent[field]
    assert path.read_bytes() == original


def test_unavailable_selected_report_has_explicit_unknown_rows(tmp_path):
    result = load_selected_run_status(
        pipeline="chembl_assay", run_id="missing", root=tmp_path
    )
    assert result["reconciliation_display"][0]["result"] == "UNKNOWN"
    assert result["reconciliation_display"][0]["meaning"] == "run_not_found"


def _failed_parent():
    parent = _parent(None)
    parent["identity"]["status"] = "failed"
    parent["plan"] = {
        "steps": [
            {
                "step_id": step_id,
                "kind": "transform",
                "transform_name": "reconcile_foreign_keys",
            }
            for step_id in ("reconcile_assay_target", "reconcile_publication_assay")
        ]
    }
    parent["execution"][1].update(
        status="failed",
        error_type="ValueError",
        error_message="reference cohort is not closed: 433 unmatched source rows; mutation blocked",
    )
    parent["execution"].append(
        {
            "step_id": "reconcile_publication_assay",
            "status": "skipped",
            "error_type": "UpstreamStepFailed",
            "error_message": "Upstream reconciliation failed before this step could execute.",
        }
    )
    return parent


def test_failed_and_skipped_fk_steps_explain_missing_metrics_without_fabricating_counts():
    parent = _failed_parent()
    original = copy.deepcopy(parent)
    rows = reconciliation_display(parent)
    assert [row["result"] for row in rows] == ["FAILED", "SKIPPED"]
    assert rows[0]["step_id"] == "reconcile_assay_target"
    assert rows[0]["meaning"] == (
        "ValueError: reference cohort is not closed: 433 unmatched source rows; mutation blocked"
    )
    assert "UpstreamStepFailed" in rows[1]["meaning"]
    assert all(row["scope"] == row["pins"] == row["limit"] == "UNKNOWN" for row in rows)
    assert parent == original


def test_failure_without_a_persisted_fk_plan_never_infers_a_comparison():
    parent = _failed_parent()
    parent.pop("plan")
    assert reconciliation_display(parent)[0]["result"] == "UNKNOWN"
    parent["plan"] = {"steps": [{"kind": "pipeline", "step_id": "run_assay"}]}
    assert reconciliation_display(parent)[0]["result"] == "N/A"


def test_foreign_parent_failure_is_not_exposed_by_an_unrelated_child(tmp_path):
    parent = _failed_parent()
    parent["execution"][0]["pipeline_run_id"] = "foreign-child"
    _write_parent(tmp_path, parent)
    rows = linked_reconciliation_display(_child(), tmp_path)
    assert rows[0]["result"] == "UNKNOWN"
    assert "433" not in json.dumps(rows)
    assert "binding mismatch" in rows[0]["meaning"]


def test_visible_workflow_failure_preserves_error_assessment_revision_and_report(
    tmp_path,
):
    child = _child()
    workflow = {
        **child["observations"]["Workflow"],
        "verdict": "ERROR",
        "reason": "workflow_failed",
    }
    workflow["facts"]["identity"]["status"] = "failed"
    draft = build_pipeline_run_report(
        identity={
            **child["identity"],
            "status": "success",
            "workflow_id": "chembl_core",
            "workflow_run_id": "parent-a",
            "workflow_step_id": "run_assay",
        },
        metrics={},
    )
    draft = replace(
        draft,
        observations={
            **{
                name: {"verdict": "OK", "reason": "checked", "facts": {}}
                for name in DOMAINS[1:]
            },
            "Workflow": workflow,
        },
    )
    write_pipeline_run_report(draft, root=tmp_path, store=FileRunReportStoreAdapter())
    path = tmp_path / "pipeline/chembl_assay/child-a/pipeline-run-report.json"
    original = path.read_bytes()
    absent = load_selected_run_status(
        pipeline="chembl_assay", run_id="child-a", root=tmp_path
    )
    _write_parent(tmp_path, _failed_parent())
    present = load_selected_run_status(
        pipeline="chembl_assay", run_id="child-a", root=tmp_path
    )
    assert present["execution_state"] == "SUCCESS"
    assert present["verdict"] == present["checks_verdict"] == "ERROR"
    assert present["reconciliation_display"][0]["result"] == "FAILED"
    assert "433" in present["reconciliation_display"][0]["meaning"]
    for field in (
        "verdict",
        "checks_verdict",
        "revision",
        "domains",
        "replay_readiness_now",
    ):
        assert present[field] == absent[field]
    assert path.read_bytes() == original


def test_complete_reference_caption_uses_persisted_completeness():
    recon = {
        **_reconciliation(),
        "reconciliation_mode": "complete-reference",
        "reference_completeness": "verified",
    }
    payload = _parent(recon)
    before = copy.deepcopy(payload)
    [row] = reconciliation_display(payload)
    assert row["mode"] == "complete-reference"
    assert row["meaning"] == "Reference completeness: verified"
    assert row["result"] == "expired 8/10; retained 2" and payload == before


@pytest.mark.parametrize("execution", [None, {}, "unavailable"])
def test_malformed_execution_cannot_invent_a_reconciliation_result(execution):
    [row] = reconciliation_display({"execution": execution})
    assert row["result"] == "UNKNOWN"
    assert row["meaning"] == "FK reconciliation evidence not recorded"


def test_unsupported_reconciliation_mode_is_explicitly_unknown():
    payload = {
        "execution": [
            {
                "step_id": "fk",
                "reconciliation": {
                    "reconciliation_mode": "future",
                    "orphan_rows_deleted": 100,
                },
            }
        ]
    }
    [row] = reconciliation_display(payload)
    assert row["step_id"] == "fk" and row["result"] == "UNKNOWN"
    assert row["meaning"] == "FK reconciliation mode absent or unsupported"
    assert "100" not in json.dumps(row)


def test_failed_step_cannot_display_stale_success_counts():
    payload = {
        "execution": [
            {
                "step_id": "fk",
                "status": "failed",
                "error_type": "IncompleteReference",
                "reconciliation": _reconciliation(),
            }
        ]
    }
    [row] = reconciliation_display(payload)
    assert row["step_id"] == "fk" and row["result"] == "FAILED"
    assert "IncompleteReference" in row["meaning"]
    assert "8/10" not in json.dumps(row)


def test_non_mapping_execution_entries_do_not_hide_a_valid_comparison():
    payload = _parent(_reconciliation())
    expected = reconciliation_display(payload)
    payload["execution"][:0] = [None, "invalid", 42, []]
    assert reconciliation_display(payload) == expected
