"""Architecture guardrails for local technical-debt planning mirrors."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

MIRROR_PATHS = (
    Path(".github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md"),
    Path("docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md"),
)


def test_local_tech_debt_planning_mirrors_are_explicitly_non_authoritative() -> None:
    for path in MIRROR_PATHS:
        content = path.read_text(encoding="utf-8")
        assert "Authoritative status source" in content, (
            f"{path} must declare its authoritative status source"
        )
        assert "Source command" in content, (
            f"{path} must record how the mirror was regenerated"
        )
        assert "Stale-warning policy" in content, (
            f"{path} must declare a stale-warning policy"
        )
        assert "sole execution authority" in content, (
            f"{path} must explicitly reject sole-authority usage"
        )


def test_local_tech_debt_planning_mirrors_do_not_present_stale_active_status() -> None:
    blueprint = Path("docs/plans/tech-debt-eradication-blueprint-v4-2026-05-31.md")
    epic = Path(".github/ISSUES/TECH-DEBT-ZERO-BURNDOWN-EPIC.md")

    assert "Status: active" not in blueprint.read_text(encoding="utf-8")
    assert "**Status**: in_progress" not in epic.read_text(encoding="utf-8")


def test_local_tech_debt_planning_mirrors_do_not_reintroduce_old_budget_claims() -> None:
    for path in MIRROR_PATHS:
        content = path.read_text(encoding="utf-8")
        assert "compatibility_test_file_max: 56" not in content, (
            f"{path} still contains a stale test-governance budget claim"
        )
