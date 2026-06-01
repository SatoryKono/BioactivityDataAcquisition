"""Unit tests for _decomposition_validation module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quality._decomposition_validation import (
    _collect_quarterly_registry_budgets,
    _parse_owner_allocations,
    _validate_burndown_registries,
    _validate_expiry_decomposition_targets_section,
    _validate_expiry_target_quarter,
    _validate_owner_decomposition_targets_section,
    _validate_owner_diversification_policy,
    _validate_priority_registry_burndown,
    _validate_program_done_criteria_section,
    _validate_target_quarter,
)

pytestmark = pytest.mark.unit


class TestCollectQuarterlyRegistryBudgets:
    """Tests for _collect_quarterly_registry_budgets."""

    def test_valid_data(self) -> None:
        """Should collect budgets from valid quarterly_targets list."""
        raw = {
            "quarterly_targets": [
                {"quarter": "2025-Q1", "registry_budgets": {"reg_a": 10, "reg_b": 5}},
                {"quarter": "2025-Q2", "registry_budgets": {"reg_a": 8, "reg_b": 3}},
            ]
        }
        result = _collect_quarterly_registry_budgets(raw)
        assert result == {
            "2025-Q1": {"reg_a": 10, "reg_b": 5},
            "2025-Q2": {"reg_a": 8, "reg_b": 3},
        }

    def test_missing_quarterly_targets(self) -> None:
        """Should return empty dict when quarterly_targets is missing."""
        result = _collect_quarterly_registry_budgets({})
        assert result == {}

    def test_not_a_list(self) -> None:
        """Should return empty dict when quarterly_targets is not a list."""
        result = _collect_quarterly_registry_budgets({"quarterly_targets": "invalid"})
        assert result == {}

    def test_skips_non_dict_items(self) -> None:
        """Should skip non-dict items in the list."""
        raw = {
            "quarterly_targets": [
                "not_a_dict",
                {"quarter": "2025-Q1", "registry_budgets": {"reg_a": 10}},
            ]
        }
        result = _collect_quarterly_registry_budgets(raw)
        assert "2025-Q1" in result

    def test_skips_missing_quarter_or_budgets(self) -> None:
        """Should skip items missing quarter or registry_budgets."""
        raw = {
            "quarterly_targets": [
                {"quarter": "2025-Q1"},  # missing registry_budgets
                {"registry_budgets": {"reg_a": 5}},  # missing quarter
            ]
        }
        result = _collect_quarterly_registry_budgets(raw)
        assert result == {}

    def test_only_int_values_included(self) -> None:
        """Should only include int values in registry_budgets."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "registry_budgets": {"reg_a": 10, "reg_b": "not_int"},
                }
            ]
        }
        result = _collect_quarterly_registry_budgets(raw)
        assert result["2025-Q1"] == {"reg_a": 10}


class TestValidateOwnerDiversificationPolicy:
    """Tests for _validate_owner_diversification_policy."""

    def test_valid_policy(self) -> None:
        """Valid policy should return parsed values."""
        raw = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q2",
                    "min_distinct_owners": 3,
                }
            }
        }
        errors: list[str] = []
        starts, min_owners = _validate_owner_diversification_policy(raw, errors)
        assert starts == (2025, 2)
        assert min_owners == 3
        assert errors == []

    def test_governance_not_dict(self) -> None:
        """Non-dict governance should return defaults."""
        raw = {"governance": "invalid"}
        errors: list[str] = []
        starts, min_owners = _validate_owner_diversification_policy(raw, errors)
        assert starts is None
        assert min_owners == 1

    def test_policy_not_dict(self) -> None:
        """Non-dict owner_diversification policy should add error."""
        raw = {"governance": {"owner_diversification": "invalid"}}
        errors: list[str] = []
        _validate_owner_diversification_policy(raw, errors)
        assert any("owner_diversification" in e for e in errors)

    def test_invalid_starts_quarter(self) -> None:
        """Invalid starts_quarter should add error."""
        raw = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "not-a-quarter",
                    "min_distinct_owners": 2,
                }
            }
        }
        errors: list[str] = []
        starts, _ = _validate_owner_diversification_policy(raw, errors)
        assert starts is None
        assert any("starts_quarter" in e for e in errors)

    def test_starts_quarter_not_string(self) -> None:
        """Non-string starts_quarter should add error."""
        raw = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": 2025,
                    "min_distinct_owners": 2,
                }
            }
        }
        errors: list[str] = []
        starts, _ = _validate_owner_diversification_policy(raw, errors)
        assert starts is None
        assert any("starts_quarter" in e for e in errors)

    def test_min_owners_zero_corrected(self) -> None:
        """min_distinct_owners=0 should be corrected to 1 with error."""
        raw = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q1",
                    "min_distinct_owners": 0,
                }
            }
        }
        errors: list[str] = []
        _, min_owners = _validate_owner_diversification_policy(raw, errors)
        assert min_owners == 1
        assert any("must be >= 1" in e for e in errors)


class TestValidateTargetQuarter:
    """Tests for _validate_target_quarter."""

    def test_valid_quarter(self) -> None:
        """Valid quarter should return (label, parsed) tuple."""
        errors: list[str] = []
        seen: set[str] = set()
        result = _validate_target_quarter(
            {"quarter": "2025-Q1"},
            "targets[0]",
            seen,
            {"2025-Q1": 10},
            errors,
        )
        assert result is not None
        assert result[0] == "2025-Q1"
        assert result[1] == (2025, 1)
        assert errors == []

    def test_missing_quarter_field(self) -> None:
        """Missing quarter field should add error and return None."""
        errors: list[str] = []
        result = _validate_target_quarter(
            {"other": "val"},
            "targets[0]",
            set(),
            {"2025-Q1": 10},
            errors,
        )
        assert result is None
        assert any("quarter" in e for e in errors)

    def test_invalid_format(self) -> None:
        """Invalid quarter format should add error and return None."""
        errors: list[str] = []
        result = _validate_target_quarter(
            {"quarter": "Q1-2025"},
            "targets[0]",
            set(),
            {"2025-Q1": 10},
            errors,
        )
        assert result is None

    def test_duplicate_quarter(self) -> None:
        """Duplicate quarter should add error and return None."""
        errors: list[str] = []
        seen = {"2025-Q1"}
        result = _validate_target_quarter(
            {"quarter": "2025-Q1"},
            "targets[1]",
            seen,
            {"2025-Q1": 10},
            errors,
        )
        assert result is None
        assert any("duplicate" in e for e in errors)

    def test_unknown_quarter_in_budget_map(self) -> None:
        """Quarter not in budget_map should add error and return None."""
        errors: list[str] = []
        result = _validate_target_quarter(
            {"quarter": "2025-Q3"},
            "targets[0]",
            set(),
            {"2025-Q1": 10},  # Q3 not in map
            errors,
        )
        assert result is None
        assert any("unknown quarter" in e for e in errors)


class TestParseOwnerAllocations:
    """Tests for _parse_owner_allocations."""

    def test_valid_allocations(self) -> None:
        """Valid allocations should return dict of owner->int."""
        errors: list[str] = []
        result = _parse_owner_allocations(
            {"allocations": {"alice": 5, "bob": 3}},
            "prefix",
            errors,
        )
        assert result == {"alice": 5, "bob": 3}
        assert errors == []

    def test_missing_allocations(self) -> None:
        """Missing allocations should add error and return None."""
        errors: list[str] = []
        result = _parse_owner_allocations({}, "prefix", errors)
        assert result is None
        assert any("allocations" in e for e in errors)

    def test_empty_allocations(self) -> None:
        """Empty allocations dict should add error and return None."""
        errors: list[str] = []
        result = _parse_owner_allocations({"allocations": {}}, "prefix", errors)
        assert result is None

    def test_invalid_owner_name(self) -> None:
        """Non-string or empty owner should add error and skip."""
        errors: list[str] = []
        result = _parse_owner_allocations(
            {"allocations": {"": 5, "valid": 3}},
            "prefix",
            errors,
        )
        assert result is not None
        assert "valid" in result
        assert any("owner" in e for e in errors)

    def test_invalid_value(self) -> None:
        """Non-int allocation value should add error."""
        errors: list[str] = []
        _parse_owner_allocations(
            {"allocations": {"alice": "not_int"}},
            "prefix",
            errors,
        )
        assert any("expected int" in e for e in errors)


class TestValidateOwnerDecompositionTargetsSection:
    """Tests for _validate_owner_decomposition_targets_section."""

    def test_valid_targets(self) -> None:
        """Valid targets should produce no errors."""
        raw = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": {"alice": 6, "bob": 4}},
            ]
        }
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            raw,
            quarter_budget_map={"2025-Q1": 10},
            owner_diversification_start=None,
            min_distinct_owners=1,
            errors=errors,
        )
        assert errors == []

    def test_missing_targets(self) -> None:
        """Missing targets should add error."""
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            {},
            quarter_budget_map={},
            owner_diversification_start=None,
            min_distinct_owners=1,
            errors=errors,
        )
        assert any("owner_decomposition_targets" in e for e in errors)

    def test_sum_mismatch(self) -> None:
        """Allocation sum not matching budget should add error."""
        raw = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": {"alice": 5}},
            ]
        }
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            raw,
            quarter_budget_map={"2025-Q1": 10},
            owner_diversification_start=None,
            min_distinct_owners=1,
            errors=errors,
        )
        assert any("sum" in e for e in errors)

    def test_diversification_violation(self) -> None:
        """Too few owners when diversification is active should add error."""
        raw = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q2", "allocations": {"alice": 10}},
            ]
        }
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            raw,
            quarter_budget_map={"2025-Q2": 10},
            owner_diversification_start=(2025, 2),
            min_distinct_owners=3,
            errors=errors,
        )
        assert any("at least" in e for e in errors)

    def test_diversification_before_start_no_error(self) -> None:
        """Quarter before diversification start should not check diversification."""
        raw = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": {"alice": 10}},
            ]
        }
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            raw,
            quarter_budget_map={"2025-Q1": 10},
            owner_diversification_start=(2025, 3),  # starts Q3
            min_distinct_owners=3,
            errors=errors,
        )
        assert errors == []

    def test_non_dict_items_skipped(self) -> None:
        """Non-dict items should add error and be skipped."""
        raw = {"owner_decomposition_targets": ["not_a_dict"]}
        errors: list[str] = []
        _validate_owner_decomposition_targets_section(
            raw,
            quarter_budget_map={},
            owner_diversification_start=None,
            min_distinct_owners=1,
            errors=errors,
        )
        assert any("expected mapping" in e for e in errors)


class TestValidateExpiryTargetQuarter:
    """Tests for _validate_expiry_target_quarter."""

    def test_valid_quarter(self) -> None:
        """Valid quarter should return parsed tuple."""
        errors: list[str] = []
        seen: set[str] = set()
        result = _validate_expiry_target_quarter(
            {"quarter": "2025-Q2"},
            "prefix",
            seen,
            errors,
        )
        assert result == (2025, 2)
        assert errors == []
        assert "2025-Q2" in seen

    def test_non_string_quarter(self) -> None:
        """Non-string quarter should add error and return None."""
        errors: list[str] = []
        result = _validate_expiry_target_quarter(
            {"quarter": 2025},
            "prefix",
            set(),
            errors,
        )
        assert result is None
        assert any("expected string" in e for e in errors)

    def test_invalid_format(self) -> None:
        """Invalid quarter format should add error and return None."""
        errors: list[str] = []
        result = _validate_expiry_target_quarter(
            {"quarter": "bad-format"},
            "prefix",
            set(),
            errors,
        )
        assert result is None

    def test_duplicate(self) -> None:
        """Duplicate quarter should add error and return None."""
        errors: list[str] = []
        seen = {"2025-Q1"}
        result = _validate_expiry_target_quarter(
            {"quarter": "2025-Q1"},
            "prefix",
            seen,
            errors,
        )
        assert result is None
        assert any("duplicate" in e for e in errors)


class TestValidateExpiryDecompositionTargetsSection:
    """Tests for _validate_expiry_decomposition_targets_section."""

    def test_valid_decreasing_targets(self) -> None:
        """Monotonically decreasing targets should produce no errors."""
        raw = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 10},
                {"quarter": "2025-Q2", "max_entries_expiring_in_quarter": 7},
                {"quarter": "2025-Q3", "max_entries_expiring_in_quarter": 5},
            ]
        }
        errors: list[str] = []
        _validate_expiry_decomposition_targets_section(raw, errors)
        assert errors == []

    def test_missing_targets(self) -> None:
        """Missing targets should add error."""
        errors: list[str] = []
        _validate_expiry_decomposition_targets_section({}, errors)
        assert any("expiry_decomposition_targets" in e for e in errors)

    def test_increasing_targets_violation(self) -> None:
        """Increasing values should add error."""
        raw = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 5},
                {
                    "quarter": "2025-Q2",
                    "max_entries_expiring_in_quarter": 10,
                },  # increases
            ]
        }
        errors: list[str] = []
        _validate_expiry_decomposition_targets_section(raw, errors)
        assert any("non-increasing" in e for e in errors)

    def test_equal_values_are_allowed(self) -> None:
        """Equal consecutive values (non-increasing) should not error."""
        raw = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 5},
                {"quarter": "2025-Q2", "max_entries_expiring_in_quarter": 5},
            ]
        }
        errors: list[str] = []
        _validate_expiry_decomposition_targets_section(raw, errors)
        assert errors == []

    def test_non_dict_items(self) -> None:
        """Non-dict items should add error and be skipped."""
        raw = {"expiry_decomposition_targets": ["not_a_dict"]}
        errors: list[str] = []
        _validate_expiry_decomposition_targets_section(raw, errors)
        assert any("expected mapping" in e for e in errors)


class TestValidateBurndownRegistries:
    """Tests for _validate_burndown_registries."""

    def test_valid_registries(self) -> None:
        """Valid registry list should return list of valid names."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            ["reg_a", "reg_b"],
            baseline_registry_names={"reg_a", "reg_b"},
            errors=errors,
        )
        assert result == ["reg_a", "reg_b"]
        assert errors == []

    def test_not_a_list(self) -> None:
        """Non-list registries should add error and return empty list."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            "not_a_list",
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result == []
        assert any("expected non-empty list" in e for e in errors)

    def test_empty_list(self) -> None:
        """Empty list should add error and return empty list."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            [],
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result == []
        assert len(errors) >= 1

    def test_unknown_registry(self) -> None:
        """Unknown registry should add error and be excluded."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            ["reg_a", "unknown_reg"],
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result == ["reg_a"]
        assert any("unknown registry" in e for e in errors)

    def test_non_string_item(self) -> None:
        """Non-string item should add error and be skipped."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            [42, "reg_a"],
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert "reg_a" in result
        assert any("registry names must be non-empty strings" in e for e in errors)

    def test_empty_string_item(self) -> None:
        """Empty-string item should add error and be skipped."""
        errors: list[str] = []
        result = _validate_burndown_registries(
            ["", "reg_a"],
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert "reg_a" in result
        assert len(errors) >= 1


class TestValidatePriorityRegistryBurndown:
    """Tests for _validate_priority_registry_burndown."""

    def test_valid_strict_decrease(self) -> None:
        """Strictly decreasing budgets should produce no errors."""
        raw = {
            "governance": {"burn_down_priorities": {"registries": ["reg_a"]}},
            "quarterly_targets": [
                {"quarter": "2025-Q1", "registry_budgets": {"reg_a": 10}},
                {"quarter": "2025-Q2", "registry_budgets": {"reg_a": 7}},
                {"quarter": "2025-Q3", "registry_budgets": {"reg_a": 4}},
            ],
        }
        errors: list[str] = []
        _validate_priority_registry_burndown(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert errors == []

    def test_governance_not_dict(self) -> None:
        """Non-dict governance should return without error."""
        raw = {"governance": "invalid"}
        errors: list[str] = []
        _validate_priority_registry_burndown(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert errors == []

    def test_burn_down_not_dict(self) -> None:
        """Non-dict burn_down_priorities should add error."""
        raw = {"governance": {"burn_down_priorities": "invalid"}}
        errors: list[str] = []
        _validate_priority_registry_burndown(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert any("burn_down_priorities" in e for e in errors)

    def test_non_decreasing_violation(self) -> None:
        """Non-decreasing budget should add burn-down violation."""
        raw = {
            "governance": {"burn_down_priorities": {"registries": ["reg_a"]}},
            "quarterly_targets": [
                {"quarter": "2025-Q1", "registry_budgets": {"reg_a": 5}},
                {"quarter": "2025-Q2", "registry_budgets": {"reg_a": 8}},  # increases
            ],
        }
        errors: list[str] = []
        _validate_priority_registry_burndown(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert any("burn-down violation" in e for e in errors)

    def test_missing_registry_in_quarter(self) -> None:
        """Registry budget missing in a quarter should add error."""
        raw = {
            "governance": {"burn_down_priorities": {"registries": ["reg_a"]}},
            "quarterly_targets": [
                {"quarter": "2025-Q1", "registry_budgets": {}},  # reg_a missing
            ],
        }
        errors: list[str] = []
        _validate_priority_registry_burndown(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert any("missing" in e for e in errors)


class TestValidateProgramDoneCriteriaSection:
    """Tests for _validate_program_done_criteria_section."""

    def test_valid_criteria(self) -> None:
        """Valid program_done_criteria should produce no errors."""
        raw = {
            "program_done_criteria": {
                "max_total_exemptions": 0,
                "min_integral_score": 95.0,
                "max_expired_entries": 0,
                "deadline_quarter": "2026-Q4",
            }
        }
        errors: list[str] = []
        _validate_program_done_criteria_section(raw, errors)
        assert errors == []

    def test_missing_section(self) -> None:
        """Missing program_done_criteria should add error."""
        errors: list[str] = []
        _validate_program_done_criteria_section({}, errors)
        assert any("program_done_criteria" in e for e in errors)

    def test_not_dict(self) -> None:
        """Non-dict section should add error."""
        errors: list[str] = []
        _validate_program_done_criteria_section(
            {"program_done_criteria": "invalid"}, errors
        )
        assert any("program_done_criteria" in e for e in errors)

    def test_invalid_min_score(self) -> None:
        """min_integral_score out of [0, 100] should add error."""
        raw = {
            "program_done_criteria": {
                "max_total_exemptions": 0,
                "min_integral_score": 150.0,
                "max_expired_entries": 0,
                "deadline_quarter": "2026-Q4",
            }
        }
        errors: list[str] = []
        _validate_program_done_criteria_section(raw, errors)
        assert any("between 0 and 100" in e for e in errors)

    def test_min_score_not_number(self) -> None:
        """Non-number min_integral_score should add error."""
        raw = {
            "program_done_criteria": {
                "max_total_exemptions": 0,
                "min_integral_score": "high",
                "max_expired_entries": 0,
                "deadline_quarter": "2026-Q4",
            }
        }
        errors: list[str] = []
        _validate_program_done_criteria_section(raw, errors)
        assert any("expected number" in e for e in errors)

    def test_invalid_deadline_quarter(self) -> None:
        """Invalid deadline_quarter should add error."""
        raw = {
            "program_done_criteria": {
                "max_total_exemptions": 0,
                "min_integral_score": 95.0,
                "max_expired_entries": 0,
                "deadline_quarter": "not-a-quarter",
            }
        }
        errors: list[str] = []
        _validate_program_done_criteria_section(raw, errors)
        assert any("deadline_quarter" in e for e in errors)
