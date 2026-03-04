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
