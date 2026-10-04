"""Scoped FK UI evidence preserves exact counts and independent assessments."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_assembly import build_pipeline_run_report
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
