"""Regression coverage for isolated campaign reports and exact visibility."""

from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from urllib.parse import parse_qs, urlsplit

import pytest
from bioetl.domain.control_plane.run_evidence_location import (
    build_run_evidence_location,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

from scripts.ops.__main__ import main as ops_main
from scripts.ops.observability import run_report_campaign as campaign
from scripts.ops.observability.campaign_report_artifacts import (
    RunReport,
    collect_reports,
    publish_reports,
    read_json,
)
from scripts.ops.observability.campaign_report_visibility import DashboardAccess

SOURCE_ID = "a" * 64
REVISION = "b" * 64
PIPELINE = RunReport("pipeline", "chembl_assay", "pipeline-id")
WORKFLOW = RunReport("workflow", "chembl_assay", "workflow-id")
QUERY = {
    "refId": "A",
    "url": "/ops/observability/pipeline-run-reports?view=recent&pipeline=${pipeline}"
    "&workflow=${workflow}&run_type=${run_type:csv}&run_id=${run_id}"
    "&lookup_run_id=${lookup_run_id:percentencode}",
}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _stage(root: Path, *, relative_data_root: str = "batch") -> None:
    snapshot = {"revision": REVISION}
    _write_json(
        root / PIPELINE.directory / "status-revisions" / f"{REVISION}.json", snapshot
    )
    _write_json(
        root / PIPELINE.commit_file,
        {
            "schema_version": "pipeline_run_report_v2",
            "identity": {
                "pipeline_name": PIPELINE.owner,
                "run_id": PIPELINE.run_id,
                "workflow_run_id": WORKFLOW.run_id,
                "status": "success",
            },
            "selected_run_snapshot": snapshot,
        },
    )
    _write_json(
        root / WORKFLOW.commit_file,
        {
            "schema_version": "workflow_run_report_v1",
            "identity": {
                "workflow_name": WORKFLOW.owner,
                "workflow_run_id": WORKFLOW.run_id,
                "status": "success",
            },
            "execution": [
                {
                    "kind": "pipeline",
                    "pipeline_name": PIPELINE.owner,
                    "pipeline_run_id": PIPELINE.run_id,
                    "status": "success",
                }
            ],
        },
    )
    for run in (PIPELINE, WORKFLOW):
        FileEvidenceLocationStore(root).register(
            build_run_evidence_location(
                kind=run.kind,
                owner=run.owner,
                run_id=run.run_id,
                runtime_source_id=SOURCE_ID,
                relative_data_root=relative_data_root,
                workflow_run_id=WORKFLOW.run_id if run == PIPELINE else None,
            )
        )


@pytest.fixture
def attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(campaign, "_load_repo_environment", lambda: None)
    monkeypatch.delenv("BIOETL_DASHBOARD_REPORT_ROOT", raising=False)
    monkeypatch.delenv("BIOETL_DASHBOARD_DATA_ROOT", raising=False)
    target = tmp_path / "reports/run-reports"
    target.mkdir(parents=True)
    data = tmp_path / "data/batch"
    data.mkdir(parents=True)
    output = tmp_path / "reports/local/attempt"
    return output, data, target


def test_campaign_retries_publication_after_grafana_misses_exact_run(
    monkeypatch, attempt
):
    output, data, target = attempt
    grafana_ready = False
    launch_count = 0

    def launch(cmd, *, env, cwd, check):
        nonlocal launch_count
        launch_count += 1
        assert cmd[1:6] == ["-m", "bioetl", "workflow", "run", "chembl_assay"]
        assert env["BIOETL_DASHBOARD_DATA_ROOT"] == str(data.parent)
        assert env["BIOETL_RUNTIME_SOURCE_ID"] == SOURCE_ID
        assert not (target / PIPELINE.commit_file).exists()
        _stage(Path(env["BIOETL_REPORT_ROOT"]))
        return CompletedProcess(cmd, 0)

    def request(self, path, *, grafana=False, body=None):
        if path.startswith("/ops/observability/workflow-run-report?"):
            return read_json(target / WORKFLOW.commit_file)
        if path.startswith("/ops/observability/pipeline-run-reports?"):
            assert parse_qs(urlsplit(path).query)["lookup_run_id"] == [PIPELINE.run_id]
            return {
                "index_state": "ok",
                "source_identity_actual": SOURCE_ID,
                "items": [{"run_id": PIPELINE.run_id}]
                if (target / PIPELINE.commit_file).is_file()
                else [],
            }
        assert grafana and path == "/api/ds/query"
        assert "lookup_run_id=pipeline-id" in body["queries"][0]["url"]
        values = [PIPELINE.run_id] if grafana_ready else ["another-run-id"]
        return {
            "results": {
                "A": {
                    "frames": [
                        {
                            "schema": {"fields": [{"name": "run_id"}]},
                            "data": {"values": [values]},
                        }
                    ]
                }
            }
        }

    monkeypatch.setattr(campaign.subprocess, "run", launch)
    monkeypatch.setattr(DashboardAccess, "preflight", lambda *_: (SOURCE_ID, QUERY))
    monkeypatch.setattr(DashboardAccess, "request", request)
    assert (
        ops_main(
            [
                "run-report-campaign",
                "run",
                "workflow",
                WORKFLOW.owner,
                "--mode",
                "publish",
                "--data-root",
                str(data),
                "--output",
                str(output),
                "--",
                "--limit",
                "1000",
            ]
        )
        == 1
    )
    receipt = read_json(output / campaign.RECEIPT)
    assert receipt["execution_status"] == "success"
    assert receipt["publication_status"] == "published_unverified"
    assert receipt["missing_reports"] == [PIPELINE.label]
    assert (target / WORKFLOW.commit_file).is_file()
    committed = (target / PIPELINE.commit_file).read_bytes()

    grafana_ready = True
    assert ops_main(["run-report-campaign", "publish", "--output", str(output)]) == 0
    assert launch_count == 1
    assert (target / PIPELINE.commit_file).read_bytes() == committed
    assert list(target.glob("pipeline/*/*/pipeline-run-report.json")) == [
        target / PIPELINE.commit_file
    ]
    assert read_json(output / campaign.RECEIPT)["publication_status"] == "verified"


def test_isolated_mode_does_not_contact_dashboard_or_publish(monkeypatch, attempt):
    output, data, target = attempt

    def launch(cmd, *, env, cwd, check):
        _stage(Path(env["BIOETL_REPORT_ROOT"]))
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(campaign.subprocess, "run", launch)
    monkeypatch.setattr(
        DashboardAccess, "preflight", lambda *_: pytest.fail("isolated preflight")
    )
    assert (
        campaign.main(
            [
                "run",
                "workflow",
                WORKFLOW.owner,
                "--mode",
                "isolated",
                "--data-root",
                str(data),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert (output / "run-reports" / PIPELINE.commit_file).exists()
    assert not (target / PIPELINE.commit_file).exists()
    assert read_json(output / campaign.RECEIPT)["publication_status"] == "not_requested"


def test_unhealthy_target_stops_before_bioetl_launch(monkeypatch, attempt, capsys):
    output, data, _ = attempt
    monkeypatch.setattr(
        campaign.subprocess, "run", lambda *_a, **_kw: pytest.fail("launch")
    )
    monkeypatch.setattr(DashboardAccess, "request", lambda *_a, **_kw: {"checks": {}})
    assert (
        ops_main(
            [
                "run-report-campaign",
                "run",
                "workflow",
                WORKFLOW.owner,
                "--mode",
                "publish",
                "--data-root",
                str(data),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert "source identity is unhealthy" in capsys.readouterr().err
    assert not output.exists()


def test_publish_rejects_foreign_locator_and_conflicting_run(tmp_path):
    source = tmp_path / "isolated"
    target = tmp_path / "shared"
    target.mkdir()
    _stage(source)
    reports = collect_reports(source, kind="workflow", owner=WORKFLOW.owner)
    with pytest.raises(ValueError, match="does not bind"):
        publish_reports(
            source, target, reports, source_id=SOURCE_ID, relative_data_root="other"
        )
    assert not (target / PIPELINE.commit_file).exists()
    _write_json(target / PIPELINE.commit_file, {"existing": True})
    with pytest.raises(ValueError, match="conflicts"):
        publish_reports(
            source, target, reports, source_id=SOURCE_ID, relative_data_root="batch"
        )
    assert read_json(target / PIPELINE.commit_file) == {"existing": True}
    assert not (target / WORKFLOW.commit_file).exists()


def test_missing_child_prevents_publication(tmp_path):
    _stage(tmp_path)
    (tmp_path / PIPELINE.commit_file).unlink()
    with pytest.raises(ValueError, match="Missing or unbound child"):
        collect_reports(tmp_path, kind="workflow", owner=WORKFLOW.owner)


def test_missing_referenced_markdown_leaves_index_empty(tmp_path):
    source = tmp_path / "isolated"
    target = tmp_path / "shared"
    target.mkdir()
    _stage(source)
    report = source / PIPELINE.commit_file
    payload = read_json(report)
    payload["artifacts"] = [{"kind": "pipeline_run_report_md", "sha256": REVISION}]
    _write_json(report, payload)
    reports = collect_reports(source, kind="workflow", owner=WORKFLOW.owner)
    with pytest.raises(ValueError, match="Referenced Markdown report is missing"):
        publish_reports(
            source, target, reports, source_id=SOURCE_ID, relative_data_root="batch"
        )
    assert not (target / PIPELINE.commit_file).exists()
