"""Run Explorer statuses must follow verified, exact-run evidence."""

import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
from urllib.parse import urlsplit

from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_report_assembly import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import DOMAINS
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http import _recent_run_presentation as presentation

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "readiness,expected",
    [
        ("READY", "OK"),
        ("BLOCKED", "ERROR"),
        ("INSUFFICIENT", "INCOMPLETE"),
        ("UNSUPPORTED", "N/A"),
        ("QUERY ERROR", "QUERY ERROR"),
    ],
)
def test_readiness_is_independent_from_processing(monkeypatch, readiness, expected):
    loader = Mock(return_value={"replay_readiness_now": readiness, "domains": []})
    monkeypatch.setattr(presentation, "load_selected_run_status", loader)
    row = {"pipeline": "chembl_assay", "run_id": "exact-id", "status": "success"}
    result = presentation.recent_run_presentation(row, root=None, manifest_port=None)
    assert result["replay_readiness_status"] == expected
    assert result["saved_evidence_status"] == "INCOMPLETE"
    assert result["data_quality_status"] == "INCOMPLETE"
    loader.assert_called_once_with(
        pipeline="chembl_assay", run_id="exact-id", root=None, manifest_port=None
    )


@pytest.mark.parametrize(
    "reason,result,expected",
    [
        ("digest_matches", "pass", "OK"),
        ("digest_mismatch", "fail", "ERROR"),
        ("artifact_missing", "fail", "INCOMPLETE"),
        ("digest_not_recorded", "unknown", "INCOMPLETE"),
    ],
)
def test_saved_evidence_checks_objects(reason, result, expected):
    assert (
        presentation._evidence_status(
            {
                "evidence_availability": "AVAILABLE",
                "evidence_completeness": "COMPLETE",
                "replay_checks": [
                    {
                        "evidence_ref": "#/artifacts/0",
                        "reason": reason,
                        "result": result,
                    }
                ],
            }
        )
        == expected
    )


def test_legacy_missing_evaluations_are_na_not_progress(monkeypatch):
    monkeypatch.setattr(
        presentation,
        "load_selected_run_status",
        lambda **kw: {
            "evidence_availability": "legacy_no_snapshot",
            "domains": [],
        },
    )
    result = presentation.recent_run_presentation(
        {
            "pipeline": "chembl_assay",
            "run_id": "exact-id",
            "workflow_id": "chembl_reference_pack",
            "provider": "chembl",
        },
        root=None,
        manifest_port=None,
    )
    assert (
        result["saved_evidence_status"]
        == result["data_quality_status"]
        == result["replay_readiness_status"]
        == "N/A"
    )
    assert result["provider"] == "chembl"
    assert result["workflow_passport_url"].endswith(
        "workflows/chembl-reference-pack.md"
    )
    assert result["pipeline_passport_url"].endswith("pipelines/chembl-assay.md")


def test_absent_workflow_has_no_passport():
    assert presentation._passport("workflows", "—") == ""


@pytest.mark.parametrize(
    "pipeline",
    [
        "chembl_assay",
        "../outside",
        "//evil.test/path",
        "javascript:alert(1)",
        "name?#%",
        "имя_pipeline",
    ],
)
def test_pipeline_passport_resolver_keeps_fixed_origin_and_encoded_path(pipeline):
    """The dashboard path field cannot introduce a scheme or another origin."""
    url = presentation._passport("pipelines", pipeline)
    parts = urlsplit(url)
    assert (parts.scheme, parts.netloc) == ("https", "github.com")
    prefix = "https://github.com/SatoryKono/BioactivityDataAcquisition/"
    path = url.partition(prefix)[2]
    assert path.startswith("blob/main/docs/04-reference/passports/pipelines/")
    assert parts.query == parts.fragment == ""
    assert "/../" not in path
    assert prefix + path == url


def test_snapshot_backed_success_run_scores_saved_evidence_ok(tmp_path):
    """#11697: finalization publishes snapshot+revision, so a new run never shows N/A."""
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_assay",
            "run_id": "run-se-ok",
            "status": "success",
            "run_type": "incremental",
            "provider": "chembl",
            "started_at": "2026-09-27T11:00:00+00:00",
            "completed_at": "2026-09-27T11:02:00+00:00",
        },
        metrics={"records_fetched": 10, "records_bronze": 10},
    )
    report = replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {"count": 0}}
            for name in DOMAINS[1:]
        },
    )
    written = write_pipeline_run_report(
        report, root=tmp_path, store=FileRunReportStoreAdapter()
    )
    payload = json.loads(written.json_path.read_text(encoding="utf-8"))
    revision = payload["selected_run_snapshot"]["revision"]
    assert (
        written.json_path.parent / "status-revisions" / f"{revision}.json"
    ).is_file()

    result = presentation.recent_run_presentation(
        {"pipeline": "chembl_assay", "run_id": "run-se-ok"},
        root=tmp_path,
        manifest_port=None,
    )
    assert result["saved_evidence_status"] == "OK"
    assert result["data_quality_status"] == "OK"
    assert result["replay_readiness_status"] == "INCOMPLETE"


def test_outside_boundary_replay_is_na_never_error_for_scored_run(monkeypatch):
    """#11697: a scored (snapshot-backed) run outside the exact-replay family stays N/A."""
    monkeypatch.setattr(
        presentation,
        "load_selected_run_status",
        lambda **kw: {
            "evidence_availability": "AVAILABLE",
            "evidence_completeness": "COMPLETE",
            "replay_readiness_now": "UNSUPPORTED",
            "replay_checks": [
                {
                    "evidence_ref": "#/artifacts/0",
                    "reason": "digest_matches",
                    "result": "pass",
                }
            ],
            "domains": [{"domain": "Data Quality", "verdict": "OK"}],
        },
    )
    result = presentation.recent_run_presentation(
        {"pipeline": "chembl_assay", "run_id": "exact-id"},
        root=None,
        manifest_port=None,
    )
    assert result["replay_readiness_status"] == "N/A"
    assert result["saved_evidence_status"] == "OK"
    assert result["data_quality_status"] == "OK"
