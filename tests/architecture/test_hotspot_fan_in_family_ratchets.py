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
