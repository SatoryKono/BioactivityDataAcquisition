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
"""Architecture guardrails for active hotspot-family internal fan-in budgets."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)

pytestmark = pytest.mark.architecture

_ENFORCED_RATCHET_STAGES = {"active", "reviewed-baseline"}


def test_active_hotspot_family_internal_fan_in_budgets_hold_reviewed_baseline() -> None:
    """Selected active hotspot families must not exceed their internal fan-in cap."""
    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families

    budgeted_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") in _ENFORCED_RATCHET_STAGES
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "max_internal_fan_in" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, (
        "Expected at least one enforced hotspot family with a fan-in budget"
    )

    for family in budgeted_families:
        family_name = family.get("name")
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_fan_in, actual_module = count_internal_fan_in(files=files)
        budget = family["bounded_growth_budgets"].get("max_internal_fan_in")
        assert isinstance(budget, int) and budget >= 0
        assert actual_fan_in <= budget, (
            f"Hotspot family {family_name} has max_internal_fan_in={actual_fan_in} "
            f"at module {actual_module}, exceeding bounded budget {budget}. "
            "Keep the family dependency ratchet stable or intentionally refresh "
            "the reviewed hotspot-family baseline under RF-06."
        )


def test_issue_10304_control_plane_replay_fan_in_has_headroom() -> None:
    """#10304: replay types/extended fold must not remain the family fan-in hub."""
    replay_root = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "control_plane"
        / "replay"
    )
    removed = (
        replay_root / "reproducibility_score_cards_types.py",
        replay_root / "reproducibility_score_cards_category_scores_extended.py",
    )
    for path in removed:
        assert not path.exists(), f"expected removed replay leaf: {path.name}"

    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    families = hotspot_policy.get("families", [])
    assert isinstance(families, list)
    family = next(
        row
        for row in families
        if isinstance(row, dict)
        and row.get("name") == "application_services_control_plane"
    )
    budgets = family.get("bounded_growth_budgets", {})
    assert isinstance(budgets, dict)
    assert budgets.get("max_internal_fan_in") == 2

    files = iter_family_python_files(
        path_prefixes=["src/bioetl/application/services/control_plane/"]
    )
    actual_fan_in, actual_module = count_internal_fan_in(files=files)
    family_budget = budgets.get("max_internal_fan_in")
    assert family_budget == 2
    assert actual_fan_in <= family_budget
    assert actual_module != (
        "bioetl.application.services.control_plane.replay."
        "reproducibility_score_cards_types"
    )

    score_card_files = [
        path
        for path in files
        if path.parent == replay_root
        and path.name.startswith("reproducibility_score_cards_")
    ]
    cluster_fan_in, cluster_module = count_internal_fan_in(files=score_card_files)
    assert cluster_fan_in < 2, (
        "replay score-card cluster max_internal_fan_in="
        f"{cluster_fan_in} at {cluster_module}; expected a line graph after #10304"
    )

