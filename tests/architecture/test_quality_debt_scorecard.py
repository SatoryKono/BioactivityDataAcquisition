"""Architecture quality-gate tests for debt scorecard governance."""

from __future__ import annotations

from bioetl.infrastructure.quality import (
    build_exemption_inventory,
    evaluate_debt_scorecard,
    load_debt_scorecard,
    validate_debt_scorecard,
)


def test_debt_scorecard_schema_is_valid() -> None:
    """Debt scorecard config must pass structural validation."""
    errors = validate_debt_scorecard()
    assert not errors, "Debt scorecard validation errors:\n" + "\n".join(
        f"  - {item}" for item in errors
    )


def test_debt_scorecard_current_quarter_within_budget() -> None:
    """Current debt inventory should stay within active quarter budgets."""
    violations, summary = evaluate_debt_scorecard()
    assert summary is not None
    assert not violations, "Debt scorecard budget violations:\n" + "\n".join(
        f"  - {item}" for item in violations
    )


def test_debt_scorecard_inventory_has_owner_and_expiry_decomposition() -> None:
    """Inventory must be decomposable by owners and expiry quarters."""
    inventory = build_exemption_inventory()
    assert inventory.total_exemptions > 0
    assert inventory.by_owner, "Owner decomposition must not be empty"
    assert inventory.by_expiry_quarter, "Expiry-quarter decomposition must not be empty"


def test_debt_scorecard_owner_targets_sum_to_quarter_budget() -> None:
    """Owner decomposition targets must reconcile with quarter max budget."""
    scorecard = load_debt_scorecard()
    max_by_quarter = {
        item["quarter"]: int(item["max_total_exemptions"])
        for item in scorecard["quarterly_targets"]
    }
    for item in scorecard.get("owner_decomposition_targets", []):
        quarter = item["quarter"]
        allocations = item.get("allocations", {})
        assert isinstance(allocations, dict)
        target_sum = sum(int(value) for value in allocations.values())
        assert quarter in max_by_quarter, (
            f"owner_decomposition_targets references unknown quarter {quarter}"
        )
        assert target_sum == max_by_quarter[quarter], (
            f"Owner allocations for {quarter} sum to {target_sum}, "
            f"expected {max_by_quarter[quarter]}"
        )
