# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for architecture debt remote-main baseline helpers."""

from __future__ import annotations

import json

import pytest

from scripts.engineering.qa import report_architecture_debt_remote_main_baseline as baseline

pytestmark = pytest.mark.unit


def test_json_blob_summary_returns_unavailable_for_none_blob() -> None:
    """_json_blob_summary should return availability:False when blob is None."""
    summary = baseline._json_blob_summary(None)

    assert summary == {"available": False}


def test_json_blob_summary_extracts_keys_from_valid_json_blob() -> None:
    """_json_blob_summary should extract expected keys from a valid JSON dict blob."""
    payload = {
        "schema_version": 1,
        "integral_score": 42,
        "weights_sum": 100,
        "coverage_xml_sha256": "abc123",
        "source_tree_sha256": "def456",
        "snapshot_date": "2026-09-01",
        "valid": True,
        "blocking_issue_count": 0,
        "extra_field": "ignored",
        "summary": {
            "source_module_count": 120,
            "unmeasured_module_count": 5,
            "repo_wide_untriaged_zero_import_candidate_count": 2,
            "retained_entrypoint_count": 10,
            "extra_nested": "ignored",
        },
    }
    blob = json.dumps(payload).encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary["available"] is True
    assert summary["schema_version"] == 1
    assert summary["integral_score"] == 42
    assert summary["weights_sum"] == 100
    assert summary["coverage_xml_sha256"] == "abc123"
    assert summary["source_tree_sha256"] == "def456"
    assert summary["snapshot_date"] == "2026-09-01"
    assert summary["valid"] is True
    assert summary["blocking_issue_count"] == 0
    assert summary["source_module_count"] == 120
    assert summary["unmeasured_module_count"] == 5
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 2
    assert summary["retained_entrypoint_count"] == 10
    assert "extra_field" not in summary
    assert "extra_nested" not in summary


def test_json_blob_summary_recovers_from_git_conflict_markers() -> None:
    """_json_blob_summary should strip conflict markers and parse valid JSON beneath."""
    conflict_blob_text = """\
<<<<<<< HEAD
|||||||
=======
{
  "schema_version": 1,
  "integral_score": 99,
  "summary": {
    "source_module_count": 200
  }
}
>>>>>>> branch-name
"""
    blob = conflict_blob_text.encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary["available"] is True
    assert summary["schema_version"] == 1
    assert summary["integral_score"] == 99
    assert summary["source_module_count"] == 200


def test_json_blob_summary_returns_available_only_for_invalid_json() -> None:
    """_json_blob_summary should return only availability for blobs that are invalid JSON even after conflict-marker stripping."""
    blob = b"not valid JSON at all"

    summary = baseline._json_blob_summary(blob)

    assert summary == {"available": True}


def test_json_blob_summary_returns_available_only_for_non_dict_json() -> None:
    """_json_blob_summary should return only availability for blobs whose JSON content is not a dict."""
    blob = json.dumps(["valid", "json", "list"]).encode("utf-8")

    summary = baseline._json_blob_summary(blob)

    assert summary == {"available": True}
