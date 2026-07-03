"""Unit tests for invariant audit rebaseline reporting."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.engineering.qa.report_invariant_audit_rebaseline import (
    build_invariant_audit_rebaseline,
    render_markdown,
    validate_rebaseline_report,
)

pytestmark = pytest.mark.unit


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")


def test_build_invariant_audit_rebaseline_classifies_all_findings() -> None:
    report = build_invariant_audit_rebaseline()

    assert report["summary"]["total_findings"] == 17
    assert report["summary"]["needs_follow_up_count"] == 0
    assert report["summary"]["classification_counts"] == {
        "duplicate-existing-issue": 2,
        "implemented": 15,
    }
    assert report["summary"]["severity_counts"] == {
        "CRITICAL": 3,
        "HIGH": 4,
        "LOW": 3,
        "MEDIUM": 7,
    }
    assert "src/bioetl/domain/batch.py" in report["summary"]["missing_cited_paths"]
    assert report["gates"]["stale_path_gate"]["status"] == "pass"
    assert report["gates"]["duplicate_issue_gate"]["status"] == "pass"


def test_validate_rebaseline_report_rejects_missing_current_anchor(
    tmp_path: Path,
) -> None:
    report = build_invariant_audit_rebaseline(tmp_path)
    finding = deepcopy(report["findings"][0])
    finding["current_source_anchors"] = ["missing.py"]
    report["findings"] = [finding, *report["findings"][1:]]

    violations = validate_rebaseline_report(report, repo_root=tmp_path)

    assert "F01: current anchor missing: missing.py" in violations


def test_validate_rebaseline_report_accepts_local_issue_export(tmp_path: Path) -> None:
    _write(tmp_path / "src.py")
    _write(tmp_path / "test.py")
    report = {
        "findings": [
            {
                "finding_id": "F01",
                "classification": "implemented",
                "cited_paths": [{"path": "old.py", "exists": False}],
                "current_source_anchors": ["src.py"],
                "current_test_anchors": ["test.py"],
                "existing_issue_anchors": ["#5444"],
            }
            for _ in range(17)
        ]
    }
    for index, row in enumerate(report["findings"], start=1):
        row["finding_id"] = f"F{index:02d}"

    violations = validate_rebaseline_report(
        report,
        repo_root=tmp_path,
        github_issues_payload={"items": [{"number": 5444}]},
    )

    assert violations == []


def test_validate_rebaseline_report_flags_unknown_issue_export_anchor(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "src.py")
    _write(tmp_path / "test.py")
    report = {
        "findings": [
            {
                "finding_id": "F01",
                "classification": "implemented",
                "cited_paths": [{"path": "old.py", "exists": False}],
                "current_source_anchors": ["src.py"],
                "current_test_anchors": ["test.py"],
                "existing_issue_anchors": ["#5444"],
            }
            for _ in range(17)
        ]
    }
    for index, row in enumerate(report["findings"], start=1):
        row["finding_id"] = f"F{index:02d}"

    violations = validate_rebaseline_report(
        report,
        repo_root=tmp_path,
        github_issues_payload={"items": [{"number": 9999}]},
    )

    assert "F01: issue anchors missing from issue export: #5444" in violations


def test_render_markdown_includes_matrix_summary() -> None:
    report = build_invariant_audit_rebaseline()

    markdown = render_markdown(report)

    assert "# Invariant Audit Rebaseline: June 2026" in markdown
    assert "Total findings: `17`" in markdown
    assert "| F01 | CRITICAL | Batch FSM lifecycle | `implemented` |" in markdown
    assert "#5461, #5462, #5463" in markdown
