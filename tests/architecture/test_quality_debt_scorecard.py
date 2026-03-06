"""Architecture quality-gate tests for debt scorecard governance."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from bioetl.infrastructure.quality import (
    build_exemption_inventory,
    evaluate_debt_scorecard,
    load_debt_scorecard,
    load_exemptions_registry,
    split_growth_violations_by_severity,
    validate_debt_scorecard,
    validate_scorecard_registry_sync,
)


def test_debt_scorecard_schema_is_valid() -> None:
    """Debt scorecard config must pass structural validation."""
    errors = validate_debt_scorecard()
    assert not errors, "Debt scorecard validation errors:\n" + "\n".join(
        f"  - {item}" for item in errors
    )


def test_debt_scorecard_governance_review_policy_requires_owner_and_removal_step() -> (
    None
):
    """Scorecard governance must require owner/removal-step for new exemptions."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    review_policy = governance.get("review_policy", {})
    assert isinstance(review_policy, dict)
    required_fields = review_policy.get("new_exemption_requires", [])
    assert isinstance(required_fields, list)
    assert "owner" in required_fields
    assert "removal_step" in required_fields

    subsystem_map = governance.get("owner_registry_q2_subsystems", {})
    assert isinstance(subsystem_map, dict)
    assert len(subsystem_map) >= 3
    owners = {
        owner
        for cfg in subsystem_map.values()
        if isinstance(cfg, dict)
        for owner in [cfg.get("owner")]
        if isinstance(owner, str) and owner.strip()
    }
    assert len(owners) >= 3


def test_debt_scorecard_enforces_budget_only_temporary_windows() -> None:
    """Grace windows policy must be budget-only and explicitly timeboxed."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    temporary = governance.get("temporary_exemptions", {})
    assert isinstance(temporary, dict)
    assert temporary.get("window_policy") == "budget-only"

    max_window_days = temporary.get("max_window_days")
    assert isinstance(max_window_days, int)
    assert 1 <= max_window_days <= 45


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
    active_owners = [
        owner
        for owner, count in inventory.by_owner.items()
        if owner != "<missing>" and count
    ]
    assert len(active_owners) >= 3, (
        "Debt registry must keep at least 3 active owners to avoid single-owner risk"
    )
    assert inventory.by_expiry_quarter, "Expiry-quarter decomposition must not be empty"


def test_debt_scorecard_registry_sync_is_valid() -> None:
    """Scorecard baseline and exemption registry must stay synchronized."""
    sync_errors = validate_scorecard_registry_sync()
    assert not sync_errors, "Debt scorecard sync violations:\n" + "\n".join(
        f"  - {item}" for item in sync_errors
    )


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


def test_owner_diversification_policy_requires_multi_owner_allocations_after_start(
    tmp_path: Path,
) -> None:
    """Owner diversification policy must enforce min owner count after start quarter."""
    scorecard = load_debt_scorecard()
    for item in scorecard.get("owner_decomposition_targets", []):
        if item.get("quarter") == "2026-Q2":
            item["allocations"] = {"@bioetl-architecture": 250}

    tmp_scorecard = tmp_path / "debt_scorecard.owner_diversification.invalid.yaml"
    tmp_scorecard.write_text(yaml.safe_dump(scorecard), encoding="utf-8")
    errors = validate_debt_scorecard(tmp_scorecard)

    assert any("expected at least" in error for error in errors), (
        "Expected owner diversification policy violation"
    )


def test_owner_diversification_policy_blocks_single_owner_inventory_after_start(
    tmp_path: Path,
) -> None:
    """Inventory with one active owner should fail once diversification policy starts."""
    registry = load_exemptions_registry()
    registries = registry.get("registries", {})
    assert isinstance(registries, dict)
    for entries in registries.values():
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if isinstance(entry, dict):
                entry["owner"] = "@bioetl-architecture"

    tmp_registry = tmp_path / "architecture_metric_exemptions.single_owner.yaml"
    tmp_registry.write_text(yaml.safe_dump(registry), encoding="utf-8")

    violations, summary = evaluate_debt_scorecard(
        registry_path=tmp_registry,
        today=date(2026, 4, 15),  # 2026-Q2
    )
    assert summary is not None
    assert any(
        "owner diversification violated" in violation for violation in violations
    ), "Expected runtime owner diversification violation for single-owner registry"


def test_owner_allocations_are_not_enforced_before_diversification_start() -> None:
    """Owner allocation limits should activate from starts_quarter, not earlier."""
    violations, summary = evaluate_debt_scorecard(today=date(2026, 3, 6))  # 2026-Q1
    assert summary is not None
    assert not any("exceeds allocation" in violation for violation in violations)


def test_program_done_criteria_applies_after_deadline(tmp_path: Path) -> None:
    """Program done criteria should produce violations once deadline quarter is reached."""
    scorecard = load_debt_scorecard()
    scorecard["program_done_criteria"] = {
        "deadline_quarter": "2026-Q1",
        "max_total_exemptions": 0,
        "min_integral_score": 100,
        "max_expired_entries": 0,
    }

    tmp_scorecard = tmp_path / "debt_scorecard.done_criteria.invalid.yaml"
    tmp_scorecard.write_text(yaml.safe_dump(scorecard), encoding="utf-8")
    violations, summary = evaluate_debt_scorecard(
        scorecard_path=tmp_scorecard,
        today=date(2026, 3, 4),
    )

    assert summary is not None
    assert any(
        violation.startswith("program done criteria violated:")
        for violation in violations
    ), "Expected at least one done-criteria violation after deadline"


def test_growth_rollout_warns_registry_section_before_cutoff() -> None:
    """Registry section violations should be warn-level during rollout window."""
    scorecard = load_debt_scorecard()
    violations = ["registry 'file_size_limits' count 120 exceeds budget 90"]

    blocking, warning = split_growth_violations_by_severity(
        violations=violations,
        scorecard=scorecard,
        today=date(2026, 4, 15),
        fallback_mode="block",
    )

    assert not blocking
    assert warning == violations


def test_growth_rollout_blocks_registry_section_after_cutoff() -> None:
    """Registry section violations should become blocking after rollout cutoff."""
    scorecard = load_debt_scorecard()
    violations = ["registry 'file_size_limits' count 120 exceeds budget 90"]

    blocking, warning = split_growth_violations_by_severity(
        violations=violations,
        scorecard=scorecard,
        today=date(2026, 7, 1),
        fallback_mode="block",
    )

    assert blocking == violations
    assert not warning


def test_growth_rollout_warns_group_section_before_cutoff() -> None:
    """Group section should be warn-level during staged rollout window."""
    scorecard = load_debt_scorecard()
    violations = ["group 'size_shape' count 400 exceeds budget 300"]

    blocking, warning = split_growth_violations_by_severity(
        violations=violations,
        scorecard=scorecard,
        today=date(2026, 3, 1),
        fallback_mode="block",
    )

    assert not blocking
    assert warning == violations


def test_growth_rollout_blocks_group_section_after_cutoff() -> None:
    """Group section must be blocking once staged rollout window is over."""
    scorecard = load_debt_scorecard()
    violations = ["group 'size_shape' count 400 exceeds budget 300"]

    blocking, warning = split_growth_violations_by_severity(
        violations=violations,
        scorecard=scorecard,
        today=date(2026, 3, 4),
        fallback_mode="block",
    )

    assert blocking == violations
    assert not warning


def test_grace_windows_require_approved_rf_when_policy_enabled(tmp_path: Path) -> None:
    """When RF-only policy is enabled, grace windows must be approved RF entries."""
    scorecard = load_debt_scorecard()
    scorecard["grace_windows"] = [
        {
            "rf_id": "TMP-001",
            "approved": False,
            "starts_on": "2026-03-01",
            "ends_on": "2026-03-15",
            "allowances": {
                "total_exemptions": 1,
                "registry_budgets": {},
                "group_budgets": {},
            },
        }
    ]

    tmp_scorecard = tmp_path / "debt_scorecard.invalid.yaml"
    tmp_scorecard.write_text(yaml.safe_dump(scorecard), encoding="utf-8")
    errors = validate_debt_scorecard(tmp_scorecard)

    assert any("allow_grace_windows_only_for_rf=true" in error for error in errors), (
        "Expected RF-only grace-window policy violation"
    )
