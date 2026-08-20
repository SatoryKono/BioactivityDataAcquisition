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
"""Architecture tests for weekly docs KPI workflow wiring."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_docs_kpi_workflow_exists_and_is_scheduled() -> None:
    workflow_path = Path(".github/workflows/docs-kpi-weekly.yml")
    assert workflow_path.exists(), "docs-kpi-weekly workflow file must exist"

    workflow = workflow_path.read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "30 4 * * 1"' in workflow
    assert "workflow_dispatch:" in workflow


def test_docs_kpi_workflow_runs_kpi_report_script() -> None:
    workflow = Path(".github/workflows/docs-kpi-weekly.yml").read_text(encoding="utf-8")

    assert "python -m scripts.docs check-kpi" in workflow
    assert "--kpi-target-not-in-nav 120" in workflow
    assert "--hard-limit-not-in-nav 135" in workflow
    assert "--max-orphans 0" in workflow
    assert "--fail-on-breach" in workflow


def test_docs_kpi_workflow_publishes_artifacts_and_summary() -> None:
    workflow = Path(".github/workflows/docs-kpi-weekly.yml").read_text(encoding="utf-8")

    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "Upload docs KPI artifacts" in workflow
    assert "reports/docs-kpi/docs-kpi-weekly.json" in workflow
    assert "reports/docs-kpi/docs-kpi-weekly.md" in workflow


def test_docs_kpi_workflow_runs_calendar_freshness_gate() -> None:
    workflow = Path(".github/workflows/docs-kpi-weekly.yml").read_text(encoding="utf-8")

    assert "python -m scripts.docs check-drift --runtime-mirrors --freshness" in workflow
    assert "Check docs runtime-mirror and freshness drift" in workflow

