"""Architecture checks for quality-governance CI gate policy."""

from __future__ import annotations

from pathlib import Path


def test_tests_workflow_blocks_expired_exemptions() -> None:
    """Merge pipeline must block when expired exemptions are present."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_GATE_MODE: block" in workflow


def test_tests_workflow_uses_staged_growth_rollout_mode() -> None:
    """Growth gate mode should be auto to honor scorecard staged rollout policy."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_GROWTH_MODE: auto" in workflow


def test_tests_workflow_enforces_budget_only_temp_windows() -> None:
    """Temporary exemption windows must stay budget-only and timeboxed in CI."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_TEMP_WINDOW_MODE: budget-only" in workflow
    assert "QUALITY_EXEMPTIONS_MAX_GRACE_WINDOW_DAYS: 45" in workflow
    assert "--temp-window-mode" in workflow
    assert "--max-grace-window-days" in workflow


def test_tests_workflow_has_fail_fast_quality_ratchet_profile() -> None:
    """CI must run staged architecture debt ratchet in strict layer order."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Quality ratchet (fail-fast: domain)" in workflow
    assert "Quality ratchet (fail-fast: application)" in workflow
    assert "Quality ratchet (fail-fast: infrastructure)" in workflow

    domain_pos = workflow.index("Quality ratchet (fail-fast: domain)")
    app_pos = workflow.index("Quality ratchet (fail-fast: application)")
    infra_pos = workflow.index("Quality ratchet (fail-fast: infrastructure)")
    assert domain_pos < app_pos < infra_pos
