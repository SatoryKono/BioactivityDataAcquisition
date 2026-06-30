"""Architecture tests for weekly quality debt report workflow wiring."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_quality_debt_weekly_workflow_exists_and_is_scheduled() -> None:
    workflow_path = Path(".github/workflows/quality-debt-weekly.yml")
    assert workflow_path.exists(), "quality-debt-weekly workflow file must exist"

    workflow = workflow_path.read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert 'cron: "45 4 * * 1"' in workflow
    assert "workflow_dispatch:" in workflow


def test_quality_debt_weekly_workflow_runs_report_script() -> None:
    workflow = Path(".github/workflows/quality-debt-weekly.yml").read_text(
        encoding="utf-8"
    )

    assert "scripts/engineering/ci/report_quality_debt_weekly.py" in workflow
    assert "--json-out reports/quality/debt-weekly.json" in workflow
    assert "--markdown-out reports/quality/debt-weekly.md" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow


def test_quality_debt_weekly_workflow_uploads_artifacts() -> None:
    workflow = Path(".github/workflows/quality-debt-weekly.yml").read_text(
        encoding="utf-8"
    )

    assert "Upload weekly debt artifacts" in workflow
    assert "reports/quality/debt-weekly.json" in workflow
    assert "reports/quality/debt-weekly.md" in workflow


def test_pr_tests_workflow_runs_debt_freeze_fail_fast_checks() -> None:
    """PR governance preflight should fail fast on debt-freeze regressions."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert "Validate technical-debt freeze ratchets" in workflow
    assert "tests/architecture/test_compatibility_freeze_guards.py" in workflow
    assert "tests/architecture/test_public_surface_importer_census_governance.py" in workflow
    assert "tests/architecture/test_runtime_uuid_seam_inventory.py" in workflow
    assert "tests/architecture/test_quality_debt_scorecard.py" in workflow
