"""Architecture quality-gate tests for debt scorecard governance."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from bioetl.infrastructure.quality._primitives import (
    _parse_quarter_label,
    _quarter_label,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    _ALLOWED_CLASSIFICATIONS,
)
from bioetl.infrastructure.quality.report_formatter import (
    _is_rollout_cutoff_stale,
)
from bioetl.infrastructure.quality import (
    build_exemption_inventory,
    evaluate_debt_scorecard,
    load_debt_scorecard,
    load_exemptions_registry,
    split_growth_violations_by_severity,
    validate_debt_scorecard,
    validate_scorecard_registry_sync,
)


def _owner_diversification_settings(
    scorecard: dict[str, object],
) -> tuple[tuple[int, int] | None, int]:
    governance = scorecard.get("governance", {})
    if not isinstance(governance, dict):
        return None, 1
    policy = governance.get("owner_diversification", {})
    if not isinstance(policy, dict):
        return None, 1
    starts_quarter_raw = policy.get("starts_quarter")
    starts_quarter = (
        _parse_quarter_label(starts_quarter_raw)
        if isinstance(starts_quarter_raw, str)
        else None
    )
    min_distinct_owners = policy.get("min_distinct_owners")
    min_distinct_owners_int = (
        min_distinct_owners if isinstance(min_distinct_owners, int) else 1
    )
    return starts_quarter, max(1, min_distinct_owners_int)


def _quarter_anchor_date(quarter: tuple[int, int]) -> date:
    year, quarter_num = quarter
    month = ((quarter_num - 1) * 3) + 2
    return date(year, month, 15)


def _previous_quarter(quarter: tuple[int, int]) -> tuple[int, int]:
    year, quarter_num = quarter
    if quarter_num == 1:
        return year - 1, 4
    return year, quarter_num - 1


def _rewrite_registry_owners(
    *,
    owner_cycle: tuple[str, ...],
) -> dict[str, object]:
    registry = load_exemptions_registry()
    registries = registry.get("registries", {})
    assert isinstance(registries, dict)
    if all(
        isinstance(entries, dict) and not entries for entries in registries.values()
    ):
        for index, registry_name in enumerate(
            sorted(registries)[: max(1, len(owner_cycle))]
        ):
            entries = registries.get(registry_name)
            if not isinstance(entries, dict):
                continue
            entries[f"{registry_name}::synthetic-{index}"] = {
                "value": 1,
                "owner": owner_cycle[index % len(owner_cycle)],
                "reason": "synthetic test seed for owner diversification coverage",
                "classification": "technical_debt",
                "linked_rf": "RF-TEST",
                "expires_on": "2026-06-30",
                "removal_step": "remove synthetic seed after scorecard evaluation",
            }
    idx = 0
    for entries in registries.values():
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            entry["owner"] = owner_cycle[idx % len(owner_cycle)]
            idx += 1
    return registry


def test_debt_scorecard_schema_is_valid() -> None:
    """Debt scorecard config must pass structural validation."""
    errors = validate_debt_scorecard()
    assert not errors, "Debt scorecard validation errors:\n" + "\n".join(
        f"  - {item}" for item in errors
    )


def test_debt_scorecard_governance_review_policy_requires_tracking_and_classification() -> (
    None
):
    """Scorecard governance must require tracking/classification for new exemptions."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    review_policy = governance.get("review_policy", {})
    assert isinstance(review_policy, dict)
    required_fields = review_policy.get("new_exemption_requires", [])
    assert isinstance(required_fields, list)
    assert "owner" in required_fields
    assert "classification" in required_fields
    assert "linked_rf" in required_fields
    assert "expires_on" in required_fields
    assert "removal_step" in required_fields
    reviewer_checks = review_policy.get("reviewer_checks", [])
    assert isinstance(reviewer_checks, list)
    assert any(
        "classification is technical_debt or intentional_exception" in str(item)
        for item in reviewer_checks
    )
    assert any("linked_rf points to active" in str(item) for item in reviewer_checks)
    assert any(
        "placeholder exemptions require concrete technical follow-up" in str(item)
        for item in reviewer_checks
    )
    assert any("2026-06-30" in str(item) for item in reviewer_checks)

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


def test_debt_scorecard_allowed_classifications_match_registry_validator() -> None:
    """Scorecard taxonomy must stay aligned with live exemption validation."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    allowed = governance.get("allowed_classifications", [])
    assert isinstance(allowed, list)
    normalized = tuple(
        sorted(item for item in allowed if isinstance(item, str) and item.strip())
    )
    assert normalized == tuple(sorted(_ALLOWED_CLASSIFICATIONS))


def test_debt_scorecard_declares_enforceable_and_historical_baselines() -> None:
    """Governance must explicitly separate live ratchet baseline from historical snapshot."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    baseline_policy = governance.get("baseline_policy", {})
    assert isinstance(baseline_policy, dict)
    assert baseline_policy.get("enforceable_section") == "baseline"
    assert baseline_policy.get("historical_section") == "historical_baseline"
    assert baseline_policy.get("registry_sync_source") == "baseline"

    baseline = scorecard.get("baseline", {})
    historical = scorecard.get("historical_baseline", {})
    assert isinstance(baseline, dict)
    assert isinstance(historical, dict)

    assert historical.get("total_exemptions", 0) >= baseline.get("total_exemptions", 0)
    baseline_by_registry = baseline.get("by_registry", {})
    historical_by_registry = historical.get("by_registry", {})
    assert isinstance(baseline_by_registry, dict)
    assert isinstance(historical_by_registry, dict)
    for registry_name, enforceable_count in baseline_by_registry.items():
        assert historical_by_registry.get(registry_name, -1) >= enforceable_count


def test_debt_scorecard_declares_explicit_coarse_budget_sync() -> None:
    """Legacy coarse regression budgets must be sourced from live scorecard policy."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    coarse = governance.get("coarse_budgets", {})
    assert isinstance(coarse, dict)

    for metric_name in (
        "ruff_error_count",
        "mypy_error_count",
        "architecture_skip_count",
    ):
        metric = coarse.get(metric_name)
        assert isinstance(metric, dict), (
            f"governance.coarse_budgets.{metric_name} must be a mapping"
        )
        assert isinstance(metric.get("max_count"), int), (
            f"governance.coarse_budgets.{metric_name}.max_count must be an int"
        )
        assert isinstance(metric.get("owner"), str) and metric["owner"], (
            f"governance.coarse_budgets.{metric_name}.owner must be non-empty"
        )
        assert isinstance(metric.get("linked_rf"), str) and metric["linked_rf"], (
            f"governance.coarse_budgets.{metric_name}.linked_rf must be non-empty"
        )
        assert isinstance(metric.get("rationale"), str) and metric["rationale"], (
            f"governance.coarse_budgets.{metric_name}.rationale must be non-empty"
        )
        assert (
            isinstance(metric.get("ratchet_policy"), str) and metric["ratchet_policy"]
        ), f"governance.coarse_budgets.{metric_name}.ratchet_policy must be non-empty"


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


def test_debt_scorecard_has_no_stale_rollout_cutoffs() -> None:
    """Live governance rollout cutoffs must be absent once they expire."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)

    rollout = governance.get("growth_section_gate_rollout", {})
    assert isinstance(rollout, dict)
    warn_until = rollout.get("warn_until_by_section", {})
    assert isinstance(warn_until, dict)

    stale_cutoffs = {
        section_key: cutoff
        for section_key, cutoff in warn_until.items()
        if _is_rollout_cutoff_stale(cutoff, today=date.today())
    }
    assert not stale_cutoffs, f"Remove stale rollout cutoffs: {stale_cutoffs}"


def test_debt_scorecard_priority_burndown_registries_cover_q2_program() -> None:
    """Priority burn-down registries must include declared Q2 maintainability focus."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)
    burn_down = governance.get("burn_down_priorities", {})
    assert isinstance(burn_down, dict)
    registries = burn_down.get("registries", [])
    assert isinstance(registries, list)

    required = {"file_size_limits", "class_size", "god_object"}
    assert required.issubset(set(registries)), (
        "governance.burn_down_priorities.registries must include "
        "file_size_limits, class_size, god_object"
    )


def test_debt_scorecard_hotspot_budgets_cover_priority_registries() -> None:
    """Each burn-down priority registry must be covered by at least one hotspot budget."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)
    burn_down = governance.get("burn_down_priorities", {})
    assert isinstance(burn_down, dict)
    priority_registries = burn_down.get("registries", [])
    assert isinstance(priority_registries, list)

    hotspot_budgets = scorecard.get("hotspot_budgets", [])
    assert isinstance(hotspot_budgets, list) and hotspot_budgets

    covered = {
        registry_name
        for item in hotspot_budgets
        if isinstance(item, dict)
        for registry_name in item.get("registry_budgets", {})
        if isinstance(registry_name, str)
    }
    missing = sorted(
        registry_name
        for registry_name in priority_registries
        if isinstance(registry_name, str) and registry_name not in covered
    )
    assert not missing, (
        "hotspot_budgets must cover burn_down_priorities registries: "
        + ", ".join(missing)
    )


def test_debt_scorecard_current_quarter_within_budget() -> None:
    """Current debt inventory should stay within active quarter budgets."""
    violations, summary = evaluate_debt_scorecard()
    assert summary is not None
    assert not violations, "Debt scorecard budget violations:\n" + "\n".join(
        f"  - {item}" for item in violations
    )


def test_debt_scorecard_current_inventory_within_hotspot_budgets() -> None:
    """Current inventory must stay within declared hotspot budgets."""
    violations, summary = evaluate_debt_scorecard()
    assert summary is not None
    hotspot_violations = [item for item in violations if item.startswith("hotspot '")]
    assert not hotspot_violations, "Hotspot budget violations:\n" + "\n".join(
        f"  - {item}" for item in hotspot_violations
    )
    assert summary.by_hotspot, "Hotspot budget summary must not be empty"


def test_debt_scorecard_inventory_has_owner_and_expiry_decomposition() -> None:
    """Inventory decomposition must match owner-diversification activation window."""
    inventory = build_exemption_inventory()
    scorecard = load_debt_scorecard()
    starts_quarter, min_distinct_owners = _owner_diversification_settings(scorecard)
    today_quarter = _parse_quarter_label(_quarter_label(date.today()))

    # When registry is empty (zero debt), decomposition checks are not applicable.
    if inventory.total_exemptions == 0:
        assert not inventory.by_owner, (
            "Empty registry must have empty owner decomposition"
        )
        assert not inventory.by_expiry_quarter, (
            "Empty registry must have empty expiry decomposition"
        )
        return

    assert inventory.by_owner, "Owner decomposition must not be empty"
    active_owners = [
        owner
        for owner, count in inventory.by_owner.items()
        if owner != "<missing>" and count
    ]
    if (
        starts_quarter is not None
        and today_quarter is not None
        and today_quarter >= starts_quarter
    ):
        assert len(active_owners) >= min_distinct_owners, (
            "Debt registry must satisfy owner diversification once activation "
            f"quarter is reached (required={min_distinct_owners})"
        )
    assert inventory.by_expiry_quarter, "Expiry-quarter decomposition must not be empty"


def test_debt_scorecard_registry_sync_is_valid() -> None:
    """Scorecard baseline and exemption registry must stay synchronized."""
    sync_errors = validate_scorecard_registry_sync()
    assert not sync_errors, "Debt scorecard sync violations:\n" + "\n".join(
        f"  - {item}" for item in sync_errors
    )


def test_debt_scorecard_registry_sync_allows_empty_god_object_registry(
    tmp_path: Path,
) -> None:
    """Empty god_object registry must still be treated as present in sync checks."""
    registry = load_exemptions_registry()
    registries = registry.get("registries", {})
    assert isinstance(registries, dict)
    registries["god_object"] = {}

    tmp_registry = tmp_path / "architecture_metric_exemptions.empty_god_object.yaml"
    tmp_registry.write_text(yaml.safe_dump(registry), encoding="utf-8")

    sync_errors = validate_scorecard_registry_sync(registry_path=tmp_registry)
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
    registry = _rewrite_registry_owners(owner_cycle=("@bioetl-architecture",))

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


def test_owner_diversification_policy_allows_two_owner_inventory_before_start(
    tmp_path: Path,
) -> None:
    """Two-owner inventory is allowed before owner-diversification start quarter."""
    scorecard = load_debt_scorecard()
    starts_quarter, _min_distinct_owners = _owner_diversification_settings(scorecard)
    assert starts_quarter is not None
    registry = _rewrite_registry_owners(
        owner_cycle=("@bioetl-architecture", "@bioetl-platform"),
    )

    tmp_registry = tmp_path / "architecture_metric_exemptions.two_owners.yaml"
    tmp_registry.write_text(yaml.safe_dump(registry), encoding="utf-8")
    before_start = _quarter_anchor_date(_previous_quarter(starts_quarter))
    violations, summary = evaluate_debt_scorecard(
        registry_path=tmp_registry,
        today=before_start,
    )
    assert summary is not None
    assert not any(
        "owner diversification violated" in violation for violation in violations
    ), "Owner diversification must not block before starts_quarter"


def test_owner_diversification_policy_blocks_two_owner_inventory_after_start(
    tmp_path: Path,
) -> None:
    """Two-owner inventory must fail from starts_quarter onward."""
    scorecard = load_debt_scorecard()
    starts_quarter, _min_distinct_owners = _owner_diversification_settings(scorecard)
    assert starts_quarter is not None
    registry = _rewrite_registry_owners(
        owner_cycle=("@bioetl-architecture", "@bioetl-platform"),
    )

    tmp_registry = tmp_path / "architecture_metric_exemptions.two_owners.yaml"
    tmp_registry.write_text(yaml.safe_dump(registry), encoding="utf-8")
    on_start = _quarter_anchor_date(starts_quarter)
    violations, summary = evaluate_debt_scorecard(
        registry_path=tmp_registry,
        today=on_start,
    )
    assert summary is not None
    assert any(
        "owner diversification violated" in violation for violation in violations
    ), "Owner diversification must block from starts_quarter"


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

    # Inject a synthetic exemption so done-criteria can detect a violation.
    tmp_registry = tmp_path / "architecture_metric_exemptions.yaml"
    tmp_registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "policy": {
                    "required_fields": [
                        "value",
                        "owner",
                        "reason",
                        "classification",
                        "linked_rf",
                        "expires_on",
                        "removal_step",
                    ]
                },
                "registries": {
                    "god_object": {
                        "FakeClass": {
                            "value": 1,
                            "owner": "@bioetl-architecture",
                            "reason": "Synthetic exemption for done-criteria test.",
                            "classification": "technical_debt",
                            "linked_rf": "RF-001",
                            "expires_on": "2026-06-30",
                            "removal_step": "Remove after test.",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    tmp_scorecard = tmp_path / "debt_scorecard.done_criteria.invalid.yaml"
    tmp_scorecard.write_text(yaml.safe_dump(scorecard), encoding="utf-8")
    violations, summary = evaluate_debt_scorecard(
        registry_path=tmp_registry,
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


def test_growth_rollout_blocks_group_section_without_active_cutoff() -> None:
    """Group sections must block once the temporary rollout override is removed."""
    scorecard = load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)
    rollout = governance.get("growth_section_gate_rollout", {})
    assert isinstance(rollout, dict)
    warn_until = rollout.get("warn_until_by_section", {})
    assert isinstance(warn_until, dict)
    assert "group:*" not in warn_until

    violations = ["group 'size_shape' count 400 exceeds budget 300"]

    blocking, warning = split_growth_violations_by_severity(
        violations=violations,
        scorecard=scorecard,
        today=date(2026, 3, 1),
        fallback_mode="block",
    )

    assert blocking == violations
    assert not warning


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
