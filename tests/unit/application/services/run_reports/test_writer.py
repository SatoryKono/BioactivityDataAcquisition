"""Unit tests for run report filesystem writers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import json
from pathlib import Path

from bioetl.application.services.run_reports.writer import (
    write_json,
    write_pipeline_run_report,
    write_workflow_run_report,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report


def test_write_pipeline_run_report(tmp_path: Path) -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.SILVER.value, 10)
    acc.record_out(StageId.SILVER.value, 8)
    acc.record_removal(
        StageId.SILVER.value,
        outcome="filtered_out",
        reason_code="FILTERED_OUT_SILVER",
        count=2,
    )
    report = build_pipeline_run_report(
        identity={
            "run_id": "abc",
            "pipeline_name": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
        },
        metrics={
            "records_fetched": 10,
            "records_bronze": 10,
            "records_silver": 8,
            "records_gold": 0,
            "records_filtered_out": 2,
            "records_quarantined": 0,
        },
        accounting=acc,
    )
    written = write_pipeline_run_report(report, root=tmp_path)
    assert written.json_path.is_file()
    assert written.markdown_path.is_file()
    payload = json.loads(written.json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pipeline_run_report_v1"
    md = written.markdown_path.read_text(encoding="utf-8")
    assert "Funnel" in md
    assert "bronze" in md.lower() or "Bronze" in md


def test_write_workflow_run_report(tmp_path: Path) -> None:
    report = build_workflow_run_report(
        identity={
            "workflow_name": "demo_wf",
            "workflow_run_id": "wf1",
            "status": "success",
        },
        plan_steps=[
            {
                "step_id": "s1",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "depends_on": [],
            }
        ],
        execution_steps=[
            {
                "step_id": "s1",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "status": "success",
                "records_extracted": 42,
            }
        ],
    )
    written = write_workflow_run_report(report, root=tmp_path)
    payload = json.loads(written.json_path.read_text(encoding="utf-8"))
    assert payload["totals"]["records_extracted_sum"] == 42
    assert "Steps" in written.markdown_path.read_text(encoding="utf-8")


def test_write_json_cleans_temporary_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "report.json"

    def _fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", _fail_replace)
    try:
        write_json(target, {"schema_version": "pipeline_run_report_v1"})
    except OSError as exc:
        assert str(exc) == "replace failed"
    else:
        raise AssertionError("write_json must surface atomic replacement failures")

    assert not target.exists()
    assert list(tmp_path.glob(".*.tmp")) == []
