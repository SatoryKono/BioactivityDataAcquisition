"""HTTP run-report ops loaders."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import json
from pathlib import Path

from bioetl.interfaces.http.run_report_ops import (
    load_pipeline_run_report_payload,
    load_workflow_run_report_payload,
)


def test_load_pipeline_report(tmp_path: Path) -> None:
    target = (
        tmp_path
        / "pipeline"
        / "chembl_activity"
        / "run1"
        / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1", "ok": True}),
        encoding="utf-8",
    )
    payload = load_pipeline_run_report_payload(
        run_id="run1",
        pipeline_name="chembl_activity",
        root=tmp_path,
    )
    assert payload is not None
    assert payload["schema_version"] == "pipeline_run_report_v1"


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert (
        load_pipeline_run_report_payload(run_id="missing", root=tmp_path) is None
    )
    assert (
        load_workflow_run_report_payload(workflow_run_id="missing", root=tmp_path)
        is None
    )


def test_load_requires_explicit_owner_selector(tmp_path: Path) -> None:
    target = (
        tmp_path
        / "pipeline"
        / "chembl_activity"
        / "run1"
        / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1"}),
        encoding="utf-8",
    )
    assert load_pipeline_run_report_payload(run_id="run1", root=tmp_path) is None


def test_load_rejects_wrong_schema_version(tmp_path: Path) -> None:
    target = (
        tmp_path
        / "workflow"
        / "demo"
        / "wf1"
        / "workflow-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1"}),
        encoding="utf-8",
    )
    assert (
        load_workflow_run_report_payload(
            workflow_run_id="wf1",
            workflow_name="demo",
            root=tmp_path,
        )
        is None
    )
