"""Run Explorer statuses must follow verified, exact-run evidence."""

from unittest.mock import Mock

import pytest

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
