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
"""Unit tests for bounded narrative drift checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.docs.checks import check_drift


pytestmark = pytest.mark.unit


def test_check_narrative_surfaces_reports_cli_only_readme_when_http_exists(
    monkeypatch, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("`INTERFACES (CLI)`\n", encoding="utf-8")

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "workflows.md").write_text("workflow guide\n", encoding="utf-8")

    src_dir = tmp_path / "src" / "bioetl" / "interfaces" / "http"
    src_dir.mkdir(parents=True)

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(check_drift, "SRC_DIR", tmp_path / "src" / "bioetl")
    monkeypatch.setattr(check_drift, "ROOT_README_PATH", readme)
    monkeypatch.setattr(check_drift, "WORKFLOW_GUIDE_PATH", docs_dir / "workflows.md")

    report = check_drift.DriftReport()
    check_drift.check_narrative_surfaces(report)

    assert report.error_count == 1
    assert "CLI-only" in report.issues[0].detail


def test_check_narrative_surfaces_allows_readme_when_http_exists_and_wording_is_current(
    monkeypatch, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("`INTERFACES (CLI / HTTP)`\n", encoding="utf-8")

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "workflows.md").write_text("workflow guide\n", encoding="utf-8")

    src_dir = tmp_path / "src" / "bioetl" / "interfaces" / "http"
    src_dir.mkdir(parents=True)

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(check_drift, "SRC_DIR", tmp_path / "src" / "bioetl")
    monkeypatch.setattr(check_drift, "ROOT_README_PATH", readme)
    monkeypatch.setattr(check_drift, "WORKFLOW_GUIDE_PATH", docs_dir / "workflows.md")

    report = check_drift.DriftReport()
    check_drift.check_narrative_surfaces(report)

    assert report.issues == []


def test_check_narrative_surfaces_reports_backlog_first_workflow_framing(
    monkeypatch, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("current root readme\n", encoding="utf-8")

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "workflows.md").write_text(
        "Workflow Control Plane backlog.\n"
        "The workflow backlog implies three different identity layers.\n"
        "Not yet fully shipped from the open backlog:\n",
        encoding="utf-8",
    )

    src_dir = tmp_path / "src" / "bioetl"
    (src_dir / "interfaces").mkdir(parents=True)

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(check_drift, "SRC_DIR", src_dir)
    monkeypatch.setattr(check_drift, "ROOT_README_PATH", readme)
    monkeypatch.setattr(check_drift, "WORKFLOW_GUIDE_PATH", docs_dir / "workflows.md")

    report = check_drift.DriftReport()
    check_drift.check_narrative_surfaces(report)

    assert report.error_count == 3
    assert all(issue.category == "narrative" for issue in report.issues)


def test_check_narrative_surfaces_allows_shipped_workflow_framing(
    monkeypatch, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("current root readme\n", encoding="utf-8")

    docs_dir = tmp_path / "docs" / "03-guides"
    docs_dir.mkdir(parents=True)
    (docs_dir / "workflows.md").write_text(
        "Workflow Control Plane.\n"
        "The workflow model uses three different identity layers.\n"
        "Future Work Outside The Active Contract\n",
        encoding="utf-8",
    )

    src_dir = tmp_path / "src" / "bioetl"
    (src_dir / "interfaces").mkdir(parents=True)

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(check_drift, "SRC_DIR", src_dir)
    monkeypatch.setattr(check_drift, "ROOT_README_PATH", readme)
    monkeypatch.setattr(check_drift, "WORKFLOW_GUIDE_PATH", docs_dir / "workflows.md")

    report = check_drift.DriftReport()
    check_drift.check_narrative_surfaces(report)

    assert report.issues == []
