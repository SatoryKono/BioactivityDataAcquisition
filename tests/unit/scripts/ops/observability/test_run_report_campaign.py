"""Regression coverage for isolated campaign reports and exact visibility."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from subprocess import CompletedProcess
from urllib.parse import parse_qs, urlsplit

import pytest
from bioetl.domain.control_plane.run_evidence_location import (
    build_run_evidence_location,
)
from bioetl.domain.run_reports.selected_status import build_snapshot
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

from scripts.ops.__main__ import main as ops_main
from scripts.ops.observability import campaign_report_visibility as visibility
from scripts.ops.observability import run_report_campaign as campaign
from scripts.ops.observability.campaign_report_artifacts import (
    RunReport,
    collect_reports,
    publish_reports,
    read_json,
)
from scripts.ops.observability.campaign_report_visibility import DashboardAccess

pytestmark = pytest.mark.unit

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
    payload = {
        "schema_version": "pipeline_run_report_v2",
        "identity": {
            "pipeline_name": PIPELINE.owner,
            "run_id": PIPELINE.run_id,
            "workflow_run_id": WORKFLOW.run_id,
            "status": "success",
        },
    }
    snapshot = build_snapshot(payload)
    _write_json(
        root / PIPELINE.directory / "status-revisions" / f"{snapshot['revision']}.json",
        snapshot,
    )
    _write_json(
        root / PIPELINE.commit_file, {**payload, "selected_run_snapshot": snapshot}
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
        assert cmd[1:] == ["-m", "scripts.ops.observability.run_report_campaign"]
        assert json.loads(env[campaign._CHILD_REQUEST]) == {
            "kind": "workflow",
            "owner": WORKFLOW.owner,
            "options": ["--limit", "1000"],
        }
        assert env["BIOETL_DASHBOARD_DATA_ROOT"] == str(data.parent)
        assert env["BIOETL_RUNTIME_SOURCE_ID"] == SOURCE_ID
        assert not (target / PIPELINE.commit_file).exists()
        _stage(Path(env["BIOETL_REPORT_ROOT"]))
        return CompletedProcess(cmd, 0)

    def request(self, path, *, grafana=False, body=None):
        if path.startswith("/ops/observability/workflow-run-report?"):
            return read_json(target / WORKFLOW.commit_file)
        if path.startswith("/ops/observability/pipeline-run-report?"):
            return read_json(target / PIPELINE.commit_file)
        if path.startswith("/ops/observability/pipeline-run-reports?"):
            assert parse_qs(urlsplit(path).query)["lookup_run_id"] == [PIPELINE.run_id]
            return {
                "index_state": "ok",
                "source_identity_actual": SOURCE_ID,
                "items": [
                    {
                        "pipeline": PIPELINE.owner,
                        "run_id": PIPELINE.run_id,
                        "report_state": "AVAILABLE",
                    }
                ]
                if (target / PIPELINE.commit_file).is_file()
                else [],
            }
        assert grafana and path == "/api/ds/query"
        assert "lookup_run_id=pipeline-id" in body["queries"][0]["url"]
        states = ["AVAILABLE" if grafana_ready else "MISSING", "AVAILABLE"]
        return {
            "results": {
                "A": {
                    "frames": [
                        {
                            "schema": {
                                "fields": [
                                    {"name": "run_id"},
                                    {"name": "report_state"},
                                ]
                            },
                            "data": {
                                "values": [[PIPELINE.run_id, "another-run-id"], states]
                            },
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


@pytest.mark.parametrize("external_mount", [False, True])
def test_isolated_mode_does_not_contact_dashboard_or_publish(
    monkeypatch, attempt, external_mount
):
    output, data, target = attempt
    alias = data.parent
    if external_mount:
        alias = campaign.REPO_ROOT.parent / "external-data"
        target = campaign.REPO_ROOT.parent / "external-reports/run-reports"
    monkeypatch.setenv("BIOETL_DASHBOARD_DATA_ROOT", str(alias))
    monkeypatch.setenv("BIOETL_DASHBOARD_REPORT_ROOT", str(target.parent))

    def launch(cmd, *, env, cwd, check):
        catalog = Path(env["BIOETL_DASHBOARD_DATA_ROOT"])
        assert catalog == data
        _write_json(
            catalog / "output/control/run_manifest/local-only.json", {"local": True}
        )
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
    assert not (alias / "output/control/run_manifest/local-only.json").exists()
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


def test_child_dispatches_validated_options_to_bioetl(monkeypatch):
    request = {
        "kind": "pipeline",
        "owner": PIPELINE.owner,
        "options": ["--limit", "1000"],
    }
    monkeypatch.setenv(campaign._CHILD_REQUEST, json.dumps(request))
    monkeypatch.setattr(campaign.sys, "argv", [])

    def launch(module, *, run_name, alter_sys):
        assert module == "bioetl" and run_name == "__main__" and alter_sys
        assert campaign.sys.argv == [
            "bioetl",
            "run",
            "--pipeline",
            PIPELINE.owner,
            "--limit",
            "1000",
        ]

    monkeypatch.setattr(campaign.runpy, "run_module", launch)
    campaign._launch_child()


def test_campaign_options_cannot_override_selected_pipeline():
    with pytest.raises(ValueError, match="cannot override the selected owner"):
        campaign._bioetl_arguments(
            "pipeline", PIPELINE.owner, ["--pipeline=chembl_target"]
        )


@pytest.mark.parametrize("state", ["MISSING", "AVAILABLE"])
def test_catalog_match_alone_does_not_verify_publication(monkeypatch, state):
    def request(self, path, **kwargs):
        if path.startswith("/ops/observability/pipeline-run-report?"):
            if state == "AVAILABLE":
                return {"status": "not_found"}
            return {
                "identity": {"pipeline_name": PIPELINE.owner, "run_id": PIPELINE.run_id}
            }
        if path.startswith("/ops/observability/pipeline-run-reports?"):
            return {
                "index_state": "ok",
                "source_identity_actual": SOURCE_ID,
                "items": [
                    {
                        "pipeline": PIPELINE.owner,
                        "run_id": PIPELINE.run_id,
                        "report_state": state,
                    }
                ],
            }
        pytest.fail(f"Unexpected query: {path}")

    monkeypatch.setattr(DashboardAccess, "request", request)
    assert (
        DashboardAccess("", "", 1).visible(PIPELINE, source_id=SOURCE_ID, query=QUERY)
        is False
    )


@pytest.mark.parametrize("status", [200, 502])
def test_preflight_queries_grafana_before_launch(monkeypatch, attempt, status):
    output, data, _ = attempt
    ready = {
        "status": "healthy",
        "source_identity_state": "aligned",
        "source_identity_actual": SOURCE_ID,
        "source_identity_expected": SOURCE_ID,
    }
    monkeypatch.setattr(visibility, "inspect_report_root_marker", lambda **_: ready)
    monkeypatch.setattr(
        visibility, "inspect_report_root_source_identity", lambda **_: ready
    )

    def request(self, path, *, grafana=False, body=None):
        if path == "/health/ready":
            return {"checks": {"report_root": ready}}
        if path.startswith("/api/dashboards/uid/"):
            return {
                "dashboard": {
                    "panels": [
                        {
                            "id": 3010,
                            "datasource": {"uid": "bioetl-ops-http"},
                            "targets": [QUERY],
                        }
                    ]
                }
            }
        assert grafana and path == "/api/ds/query"
        assert (
            "lookup_run_id=00000000-0000-0000-0000-000000000000"
            in body["queries"][0]["url"]
        )
        return {"results": {"A": {"status": status, "frames": []}}}

    monkeypatch.setattr(DashboardAccess, "request", request)
    if status == 200:
        assert DashboardAccess("", "", 1).preflight(attempt[2])[0] == SOURCE_ID
    else:
        monkeypatch.setattr(
            campaign.subprocess, "run", lambda *_, **__: pytest.fail("launch")
        )
        assert (
            campaign.main(
                [
                    "run",
                    "pipeline",
                    PIPELINE.owner,
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
        assert not output.exists()


def test_later_locator_conflict_leaves_earlier_report_unpublished(tmp_path):
    source = tmp_path / "isolated"
    target = tmp_path / "shared"
    target.mkdir()
    _stage(source)
    FileEvidenceLocationStore(target).register(
        build_run_evidence_location(
            kind=WORKFLOW.kind,
            owner=WORKFLOW.owner,
            run_id=WORKFLOW.run_id,
            runtime_source_id=SOURCE_ID,
            relative_data_root="other",
        )
    )
    reports = collect_reports(source, kind="workflow", owner=WORKFLOW.owner)
    with pytest.raises(ValueError, match="locator conflicts"):
        publish_reports(
            source, target, reports, source_id=SOURCE_ID, relative_data_root="batch"
        )
    assert not (target / PIPELINE.commit_file).exists()


def test_tampered_copies_of_status_revision_are_rejected(tmp_path):
    source = tmp_path / "isolated"
    target = tmp_path / "shared"
    target.mkdir()
    _stage(source)
    report = read_json(source / PIPELINE.commit_file)
    snapshot = report["selected_run_snapshot"]
    snapshot["assessment"]["verdict"] = "tampered"
    _write_json(source / PIPELINE.commit_file, report)
    _write_json(
        source
        / PIPELINE.directory
        / "status-revisions"
        / f"{snapshot['revision']}.json",
        snapshot,
    )
    reports = collect_reports(source, kind="workflow", owner=WORKFLOW.owner)
    with pytest.raises(ValueError, match="Invalid committed status snapshot"):
        publish_reports(
            source, target, reports, source_id=SOURCE_ID, relative_data_root="batch"
        )
    assert not (target / PIPELINE.commit_file).exists()


def test_grafana_http_outside_loopback_stops_before_reading_credentials(monkeypatch):
    monkeypatch.setattr(
        visibility, "resolve_grafana_password", lambda: pytest.fail("credentials")
    )
    access = DashboardAccess(
        "http://127.0.0.1:8000", "http://host.docker.internal:3000", 1
    )
    with pytest.raises(ValueError, match="HTTPS outside loopback"):
        access.request("/api/ds/query", grafana=True)


def test_forwarded_pipeline_override_is_rejected_before_launch(monkeypatch, attempt):
    output, data, _ = attempt
    monkeypatch.setattr(
        campaign.subprocess, "run", lambda *_a, **_kw: pytest.fail("launch")
    )
    with pytest.raises(SystemExit) as error:
        campaign.main(
            [
                "run",
                "pipeline",
                PIPELINE.owner,
                "--mode",
                "isolated",
                "--data-root",
                str(data),
                "--output",
                str(output),
                "--",
                "--pipeline=other_pipeline",
            ]
        )
    assert error.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize("host", ["grafana", "host.docker.internal", "dev.localhost"])
def test_grafana_rejects_cleartext_outside_loopback(monkeypatch, host):
    monkeypatch.setattr(
        visibility.urllib.request,
        "build_opener",
        lambda *_: pytest.fail("network request"),
    )
    access = DashboardAccess("http://127.0.0.1:8000", f"http://{host}:3000", 10)
    with pytest.raises(ValueError, match="requires HTTPS outside loopback"):
        access.request("/api/dashboards", grafana=True)


@pytest.mark.parametrize(
    "grafana_url",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
        "https://grafana:3000",
    ],
)
def test_grafana_auth_uses_https_or_loopback(monkeypatch, grafana_url):
    class Opener:
        def open(self, request, *, timeout):
            assert request.full_url == f"{grafana_url}/api/dashboards"
            assert request.get_header("Authorization") == "Basic test-only"
            assert timeout == 10
            return BytesIO(b'{"healthy": true}')

    monkeypatch.setattr(visibility, "resolve_grafana_password", lambda: "test-password")
    monkeypatch.setattr(visibility, "_auth_header", lambda *_: "Basic test-only")
    monkeypatch.setattr(visibility.urllib.request, "build_opener", lambda *_: Opener())
    access = DashboardAccess("http://127.0.0.1:8000", grafana_url, 10)
    assert access.request("/api/dashboards", grafana=True) == {"healthy": True}
