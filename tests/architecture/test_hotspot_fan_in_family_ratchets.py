"""Architecture guardrails for active hotspot-family internal fan-in budgets."""

from __future__ import annotations

from scripts.engineering.qa.hotspot_family_metrics import (
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)


def test_active_hotspot_family_internal_fan_in_budgets_hold_reviewed_baseline() -> None:
    """Selected active hotspot families must not exceed their internal fan-in cap."""
    scorecard = load_scorecard()
    hotspot_policy = scorecard.get("report_only_hotspot_families", {})
    assert isinstance(hotspot_policy, dict)

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families

    budgeted_families = [
        family
        for family in families
        if isinstance(family, dict)
        and family.get("ratchet_stage") == "active"
        and isinstance(family.get("bounded_growth_budgets"), dict)
        and "max_internal_fan_in" in family["bounded_growth_budgets"]
    ]
    assert budgeted_families, "Expected at least one active family with a fan-in budget"

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
            "Keep the family dependency ratchet stable or rebaseline the reviewed "
            "scorecard snapshot intentionally under RF-06."
        )
