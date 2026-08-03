# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for debt scorecard scoring calculations."""

from __future__ import annotations

from collections import Counter

import pytest

from bioetl.infrastructure.quality.scoring import (
    _compute_group_counts,
    _evaluate_expiry_cap,
    _evaluate_group_budgets,
    _evaluate_owner_allocations,
    _evaluate_owner_diversification,
    _evaluate_program_done_criteria,
    _evaluate_registry_budgets,
    _expiry_cap_for_quarter,
    _owner_allocations_for_quarter,
    compute_integral_debt_score,
)

pytestmark = pytest.mark.unit


class TestComputeIntegralDebtScore:
    """Tests for compute_integral_debt_score."""

    def test_perfect_score_no_exemptions(self) -> None:
        """Zero exemptions should give 100.0."""
        score = compute_integral_debt_score(
            total_exemptions=0, expired_entries=0, baseline_total=10
        )
        assert score == pytest.approx(100.0)

    def test_zero_baseline_returns_zero(self) -> None:
        """Zero baseline_total should return 0.0."""
        score = compute_integral_debt_score(
            total_exemptions=5, expired_entries=0, baseline_total=0
        )
        assert score == pytest.approx(0.0)

    def test_negative_baseline_returns_zero(self) -> None:
        """Negative baseline_total should return 0.0."""
        score = compute_integral_debt_score(
            total_exemptions=5, expired_entries=0, baseline_total=-1
        )
        assert score == pytest.approx(0.0)

    def test_all_expired(self) -> None:
        """All exemptions expired should reduce score."""
        score = compute_integral_debt_score(
            total_exemptions=10, expired_entries=10, baseline_total=10
        )
        # debt_reduction = 0 (100% of baseline is exemptions)
        # expiry_health = 0 (all expired)
        assert score == pytest.approx(0.0)

    def test_half_exemptions_half_expired(self) -> None:
        """Partial expiry with partial exemptions."""
        score = compute_integral_debt_score(
            total_exemptions=5, expired_entries=2, baseline_total=10
        )
        assert score == pytest.approx(57.0)

    def test_score_is_rounded(self) -> None:
        """Score should be rounded to 2 decimal places."""
        score = compute_integral_debt_score(
            total_exemptions=3, expired_entries=1, baseline_total=7
        )
        assert isinstance(score, float)
        assert str(score).count(".") <= 1
        parts = str(score).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 2


class TestComputeGroupCounts:
    """Tests for _compute_group_counts."""

    def test_basic_grouping(self) -> None:
        """Should sum registry counts per group."""
        by_registry = {"reg_a": 3, "reg_b": 5, "reg_c": 2}
        registry_groups = {
            "group1": {"registries": ["reg_a", "reg_b"]},
            "group2": {"registries": ["reg_c"]},
        }
        result = _compute_group_counts(
            by_registry=by_registry, registry_groups=registry_groups
        )
        assert result == {"group1": 8, "group2": 2}

    def test_missing_registry_counted_as_zero(self) -> None:
        """Missing registries should be counted as 0."""
        by_registry = {"reg_a": 5}
        registry_groups = {
            "group1": {"registries": ["reg_a", "reg_missing"]},
        }
        result = _compute_group_counts(
            by_registry=by_registry, registry_groups=registry_groups
        )
        assert result == {"group1": 5}

    def test_compute_group_counts__empty_groups__9bf2db69(self) -> None:
        """Empty registry_groups should return empty dict."""
        result = _compute_group_counts(by_registry={"a": 1}, registry_groups={})
        assert result == {}


class TestEvaluateRegistryBudgets:
    """Tests for _evaluate_registry_budgets."""

    def test_within_budget_no_violations(self) -> None:
        """No violations when within budget."""
        violations = _evaluate_registry_budgets(
            by_registry={"reg_a": 5},
            target_registry_budgets={"reg_a": 10},
            allowance_by_registry=Counter(),
        )
        assert violations == []

    def test_over_budget_violation(self) -> None:
        """Should report violation when count exceeds budget."""
        violations = _evaluate_registry_budgets(
            by_registry={"reg_a": 15},
            target_registry_budgets={"reg_a": 10},
            allowance_by_registry=Counter(),
        )
        assert len(violations) == 1
        assert "reg_a" in violations[0]
        assert "15" in violations[0]

    def test_allowance_extends_budget(self) -> None:
        """Allowance should extend the budget."""
        violations = _evaluate_registry_budgets(
            by_registry={"reg_a": 15},
            target_registry_budgets={"reg_a": 10},
            allowance_by_registry=Counter({"reg_a": 5}),
        )
        assert violations == []

    def test_exactly_at_budget_no_violation(self) -> None:
        """Exactly at budget should not violate."""
        violations = _evaluate_registry_budgets(
            by_registry={"reg_a": 10},
            target_registry_budgets={"reg_a": 10},
            allowance_by_registry=Counter(),
        )
        assert violations == []


class TestEvaluateGroupBudgets:
    """Tests for _evaluate_group_budgets."""

    def test_within_budget(self) -> None:
        """No violations when within group budget."""
        violations = _evaluate_group_budgets(
            by_group={"group1": 5},
            target_group_budgets={"group1": 10},
            allowance_by_group=Counter(),
        )
        assert violations == []

    def test_over_budget(self) -> None:
        """Should report violation for over-budget groups."""
        violations = _evaluate_group_budgets(
            by_group={"group1": 15},
            target_group_budgets={"group1": 10},
            allowance_by_group=Counter(),
        )
        assert len(violations) == 1
        assert "group1" in violations[0]

    def test_allowance_extends_group_budget(self) -> None:
        """Group allowance should extend the budget."""
        violations = _evaluate_group_budgets(
            by_group={"group1": 12},
            target_group_budgets={"group1": 10},
            allowance_by_group=Counter({"group1": 5}),
        )
        assert violations == []


class TestOwnerAllocationsForQuarter:
    """Tests for _owner_allocations_for_quarter."""

    def test_returns_allocations_for_matching_quarter(self) -> None:
        """Should return allocations for the matching quarter."""
        scorecard = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": {"alice": 5, "bob": 3}},
            ]
        }
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q1")
        assert result == {"alice": 5, "bob": 3}

    def test_returns_empty_for_no_match(self) -> None:
        """Should return empty dict when quarter doesn't match."""
        scorecard = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": {"alice": 5}},
            ]
        }
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q2")
        assert result == {}

    def test_returns_empty_when_targets_not_list(self) -> None:
        """Should return empty dict when targets is not a list."""
        scorecard = {"owner_decomposition_targets": "invalid"}
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q1")
        assert result == {}

    def test_returns_empty_when_targets_missing(self) -> None:
        """Should return empty dict when targets key is missing."""
        result = _owner_allocations_for_quarter(scorecard={}, quarter="2025-Q1")
        assert result == {}

    def test_returns_empty_when_allocations_not_dict(self) -> None:
        """Should return empty dict when allocations is not a dict."""
        scorecard = {
            "owner_decomposition_targets": [
                {"quarter": "2025-Q1", "allocations": "invalid"},
            ]
        }
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q1")
        assert result == {}

    def test_for_quarter__skips_non_dict_items__b6fb17ed(self) -> None:
        """Should skip non-dict items in targets list."""
        scorecard = {
            "owner_decomposition_targets": [
                "invalid",
                {"quarter": "2025-Q1", "allocations": {"alice": 5}},
            ]
        }
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q1")
        assert result == {"alice": 5}

    def test_filters_non_string_owners(self) -> None:
        """Should only include string-keyed, int-valued allocations."""
        scorecard = {
            "owner_decomposition_targets": [
                {
                    "quarter": "2025-Q1",
                    "allocations": {"alice": 5, 123: 3, "bob": "not_int"},
                },
            ]
        }
        result = _owner_allocations_for_quarter(scorecard=scorecard, quarter="2025-Q1")
        assert result == {"alice": 5}


class TestEvaluateOwnerAllocations:
    """Tests for _evaluate_owner_allocations."""

    def test_within_allocation(self) -> None:
        """No violations when within allocation."""
        violations = _evaluate_owner_allocations(
            by_owner={"alice": 5},
            allocations={"alice": 10},
            quarter="2025-Q1",
        )
        assert violations == []

    def test_over_allocation(self) -> None:
        """Should report violation for over-allocation."""
        violations = _evaluate_owner_allocations(
            by_owner={"alice": 15},
            allocations={"alice": 10},
            quarter="2025-Q1",
        )
        assert len(violations) == 1
        assert "alice" in violations[0]

    def test_missing_owner_skipped(self) -> None:
        """<missing> owner should be skipped."""
        violations = _evaluate_owner_allocations(
            by_owner={"<missing>": 100},
            allocations={},
            quarter="2025-Q1",
        )
        assert violations == []

    def test_owner_not_in_allocations(self) -> None:
        """Owner not in allocations gets budget of 0."""
        violations = _evaluate_owner_allocations(
            by_owner={"alice": 1},
            allocations={},
            quarter="2025-Q1",
        )
        assert len(violations) == 1


class TestEvaluateOwnerDiversification:
    """Tests for _evaluate_owner_diversification."""

    def test_sufficient_owners_no_violation(self) -> None:
        """No violation when enough distinct owners."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q1",
                    "min_distinct_owners": 2,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 3, "bob": 2},
            scorecard=scorecard,
            quarter="2025-Q1",
        )
        assert violations == []

    def test_insufficient_owners_violation(self) -> None:
        """Should report violation when too few owners."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q1",
                    "min_distinct_owners": 3,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 3, "bob": 2},
            scorecard=scorecard,
            quarter="2025-Q1",
        )
        assert len(violations) == 1
        assert "diversification" in violations[0]

    def test_before_start_quarter_no_check(self) -> None:
        """Should not check if current quarter is before starts_quarter."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q3",
                    "min_distinct_owners": 5,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1},
            scorecard=scorecard,
            quarter="2025-Q1",
        )
        assert violations == []

    def test_missing_governance_no_violation(self) -> None:
        """No violation when governance section is missing."""
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1}, scorecard={}, quarter="2025-Q1"
        )
        assert violations == []

    def test_owner_diversification__governance_not_dict__2a21416e(self) -> None:
        """No violation when governance is not a dict."""
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1},
            scorecard={"governance": "invalid"},
            quarter="2025-Q1",
        )
        assert violations == []

    def test_owner_diversification__policy_not_dict__529b780f(self) -> None:
        """No violation when policy is not a dict."""
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1},
            scorecard={"governance": {"owner_diversification": "invalid"}},
            quarter="2025-Q1",
        )
        assert violations == []

    def test_missing_policy_fields(self) -> None:
        """No violation when required policy fields are missing."""
        scorecard = {
            "governance": {"owner_diversification": {"starts_quarter": "2025-Q1"}}
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1}, scorecard=scorecard, quarter="2025-Q1"
        )
        assert violations == []

    def test_min_distinct_owners_zero(self) -> None:
        """Should skip check when min_distinct_owners < 1."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q1",
                    "min_distinct_owners": 0,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={}, scorecard=scorecard, quarter="2025-Q1"
        )
        assert violations == []

    def test_missing_owner_excluded(self) -> None:
        """<missing> owner should not count as active."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2025-Q1",
                    "min_distinct_owners": 2,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 3, "<missing>": 5},
            scorecard=scorecard,
            quarter="2025-Q1",
        )
        assert len(violations) == 1

    def test_owner_diversification__quarter_format__6573e5ae(self) -> None:
        """Invalid quarter format should not cause errors."""
        scorecard = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "invalid",
                    "min_distinct_owners": 2,
                }
            }
        }
        violations = _evaluate_owner_diversification(
            by_owner={"alice": 1}, scorecard=scorecard, quarter="2025-Q1"
        )
        assert violations == []


class TestExpiryCap:
    """Tests for _expiry_cap_for_quarter."""

    def test_returns_cap_for_matching_quarter(self) -> None:
        """Should return cap for matching quarter."""
        scorecard = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 5},
            ]
        }
        assert _expiry_cap_for_quarter(scorecard=scorecard, quarter="2025-Q1") == 5

    def test_scoring_expiry_cap__none_for_no_match__68f5b2c6(self) -> None:
        """Should return None when quarter doesn't match."""
        scorecard = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 5},
            ]
        }
        assert _expiry_cap_for_quarter(scorecard=scorecard, quarter="2025-Q2") is None

    def test_returns_none_when_targets_not_list(self) -> None:
        """Should return None when targets is not a list."""
        scorecard = {"expiry_decomposition_targets": "invalid"}
        assert _expiry_cap_for_quarter(scorecard=scorecard, quarter="2025-Q1") is None

    def test_returns_none_when_cap_not_int(self) -> None:
        """Should return None when cap is not an int."""
        scorecard = {
            "expiry_decomposition_targets": [
                {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": "invalid"},
            ]
        }
        assert _expiry_cap_for_quarter(scorecard=scorecard, quarter="2025-Q1") is None

    def test_returns_none_when_targets_missing(self) -> None:
        """Should return None when key is missing."""
        assert _expiry_cap_for_quarter(scorecard={}, quarter="2025-Q1") is None


class TestEvaluateExpiryCap:
    """Tests for _evaluate_expiry_cap."""

    def test_no_cap_no_violations(self) -> None:
        """No violations when cap is None."""
        violations = _evaluate_expiry_cap(
            by_expiry_quarter={"2025-Q1": 100}, quarter="2025-Q1", cap=None
        )
        assert violations == []

    def test_within_cap(self) -> None:
        """No violations when within cap."""
        violations = _evaluate_expiry_cap(
            by_expiry_quarter={"2025-Q1": 3}, quarter="2025-Q1", cap=5
        )
        assert violations == []

    def test_exceeds_cap(self) -> None:
        """Should report violation when exceeding cap."""
        violations = _evaluate_expiry_cap(
            by_expiry_quarter={"2025-Q1": 10}, quarter="2025-Q1", cap=5
        )
        assert len(violations) == 1
        assert "10" in violations[0]


class TestEvaluateProgramDoneCriteria:
    """Tests for _evaluate_program_done_criteria."""

    def test_no_criteria_no_violations(self) -> None:
        """No violations when criteria is missing."""
        violations = _evaluate_program_done_criteria(
            scorecard={},
            current_quarter="2025-Q4",
            total_exemptions=100,
            integral_score=50.0,
            expired_entries=50,
        )
        assert violations == []

    def test_criteria_not_dict(self) -> None:
        """No violations when criteria is not a dict."""
        violations = _evaluate_program_done_criteria(
            scorecard={"program_done_criteria": "invalid"},
            current_quarter="2025-Q4",
            total_exemptions=100,
            integral_score=50.0,
            expired_entries=50,
        )
        assert violations == []

    def test_before_deadline_no_check(self) -> None:
        """Should not check when current quarter is before deadline."""
        scorecard = {
            "program_done_criteria": {
                "deadline_quarter": "2026-Q4",
                "max_total_exemptions": 0,
            }
        }
        violations = _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter="2025-Q1",
            total_exemptions=100,
            integral_score=50.0,
            expired_entries=50,
        )
        assert violations == []

    def test_at_deadline_check_max_total_exemptions(self) -> None:
        """Should check exemptions at/after deadline."""
        scorecard = {
            "program_done_criteria": {
                "deadline_quarter": "2025-Q4",
                "max_total_exemptions": 5,
            }
        }
        violations = _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter="2025-Q4",
            total_exemptions=10,
            integral_score=100.0,
            expired_entries=0,
        )
        assert len(violations) == 1
        assert "total_exemptions" in violations[0]

    def test_at_deadline_check_min_integral_score(self) -> None:
        """Should check integral score at/after deadline."""
        scorecard = {
            "program_done_criteria": {
                "deadline_quarter": "2025-Q4",
                "min_integral_score": 80.0,
            }
        }
        violations = _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter="2025-Q4",
            total_exemptions=0,
            integral_score=50.0,
            expired_entries=0,
        )
        assert len(violations) == 1
        assert "integral_score" in violations[0]

    def test_at_deadline_check_max_expired_entries(self) -> None:
        """Should check expired entries at/after deadline."""
        scorecard = {
            "program_done_criteria": {
                "deadline_quarter": "2025-Q4",
                "max_expired_entries": 2,
            }
        }
        violations = _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter="2025-Q4",
            total_exemptions=0,
            integral_score=100.0,
            expired_entries=5,
        )
        assert len(violations) == 1
        assert "expired_entries" in violations[0]

    def test_multiple_violations(self) -> None:
        """Should report all violated criteria."""
        scorecard = {
            "program_done_criteria": {
                "deadline_quarter": "2025-Q4",
                "max_total_exemptions": 0,
                "min_integral_score": 100.0,
                "max_expired_entries": 0,
            }
        }
        violations = _evaluate_program_done_criteria(
            scorecard=scorecard,
            current_quarter="2025-Q4",
            total_exemptions=10,
            integral_score=50.0,
            expired_entries=5,
        )
        assert len(violations) == 3
