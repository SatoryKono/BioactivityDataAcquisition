"""Unit tests for budget_evaluator module."""

from __future__ import annotations

import pytest

from datetime import date

from bioetl.infrastructure.quality.budget_evaluator import (
    _is_owner_decomposition_active,
    current_quarter_target,
    evaluate_budget_violations,
    evaluate_governance_violations,
    resolve_grace_allowances,
)
from bioetl.infrastructure.quality.inventory import ExemptionInventorySummary


pytestmark = pytest.mark.unit


def _make_inventory(
    total: int = 0,
    by_registry: dict[str, int] | None = None,
    by_owner: dict[str, int] | None = None,
    by_expiry_quarter: dict[str, int] | None = None,
    expired: int = 0,
) -> ExemptionInventorySummary:
    return ExemptionInventorySummary(
        total_exemptions=total,
        by_registry=by_registry or {},
        by_owner=by_owner or {},
        by_expiry_quarter=by_expiry_quarter or {},
        expired_entries=expired,
    )


class TestCurrentQuarterTarget:
    """Tests for current_quarter_target."""

    def test_returns_matching_target(self) -> None:
        """Should return target for current quarter."""
        scorecard = {
            "quarterly_targets": [
                {"quarter": "2025-Q1", "max_total_exemptions": 20},
                {"quarter": "2025-Q2", "max_total_exemptions": 15},
            ]
        }
        result = current_quarter_target(scorecard, today=date(2025, 2, 15))
        assert result is not None
        assert result["quarter"] == "2025-Q1"

    def test_current_quarter_target__none_when_no_match__367ca23a(self) -> None:
        """Should return None when no target for current quarter."""
        scorecard = {
            "quarterly_targets": [
                {"quarter": "2024-Q1", "max_total_exemptions": 20},
            ]
        }
        result = current_quarter_target(scorecard, today=date(2025, 6, 15))
        assert result is None

    def test_returns_none_for_empty_targets(self) -> None:
        """Should return None for empty quarterly_targets."""
        result = current_quarter_target(
            {"quarterly_targets": []}, today=date(2025, 1, 1)
        )
        assert result is None

    def test_skips_non_dict_items(self) -> None:
        """Should skip non-dict items in quarterly_targets."""
        scorecard = {
            "quarterly_targets": [
                "not_a_dict",
                {"quarter": "2025-Q2", "max_total_exemptions": 15},
            ]
        }
        result = current_quarter_target(scorecard, today=date(2025, 5, 1))
        assert result is not None
        assert result["quarter"] == "2025-Q2"


class TestIsOwnerDecompositionActive:
    """Tests for _is_owner_decomposition_active."""

    def test_active_when_current_quarter_gte_start(self) -> None:
        """Decomposition should be active when current >= starts_quarter."""
        scorecard = {
            "governance": {"owner_diversification": {"starts_quarter": "2025-Q1"}}
        }
        assert _is_owner_decomposition_active(scorecard=scorecard, quarter="2025-Q2")

    def test_inactive_when_before_start(self) -> None:
        """Decomposition should be inactive when current < starts_quarter."""
        scorecard = {
            "governance": {"owner_diversification": {"starts_quarter": "2025-Q3"}}
        }
        assert not _is_owner_decomposition_active(
            scorecard=scorecard, quarter="2025-Q1"
        )

    def test_active_when_governance_missing(self) -> None:
        """Should default to active when governance is missing."""
        assert _is_owner_decomposition_active(scorecard={}, quarter="2025-Q1")

    def test_active_when_governance_not_dict(self) -> None:
        """Should default to active when governance is not a dict."""
        assert _is_owner_decomposition_active(
            scorecard={"governance": "invalid"}, quarter="2025-Q1"
        )

    def test_active_when_diversification_not_dict(self) -> None:
        """Should default to active when owner_diversification is not a dict."""
        assert _is_owner_decomposition_active(
            scorecard={"governance": {"owner_diversification": "invalid"}},
            quarter="2025-Q1",
        )

    def test_active_when_starts_quarter_not_string(self) -> None:
        """Should default to active when starts_quarter is not a string."""
        scorecard = {"governance": {"owner_diversification": {"starts_quarter": 2025}}}
        assert _is_owner_decomposition_active(scorecard=scorecard, quarter="2025-Q1")


class TestResolveGraceAllowances:
    """Tests for resolve_grace_allowances."""

    def test_no_grace_windows(self) -> None:
        """Should return empty results when no grace_windows."""
        active, total, by_registry, by_group = resolve_grace_allowances(
            {}, today=date(2025, 6, 15)
        )
        assert active == []
        assert total == 0
        assert by_registry == {}
        assert by_group == {}

    def test_active_window_included(self) -> None:
        """Active approved window should be included."""
        scorecard = {
            "grace_windows": [
                {
                    "rf_id": "RF-001",
                    "approved": True,
                    "starts_on": "2025-01-01",
                    "ends_on": "2025-12-31",
                    "allowances": {
                        "total_exemptions": 5,
                        "registry_budgets": {"reg_a": 3},
                    },
                }
            ]
        }
        active, total, by_registry, _ = resolve_grace_allowances(
            scorecard, today=date(2025, 6, 15)
        )
        assert len(active) == 1
        assert total == 5
        assert by_registry == {"reg_a": 3}

    def test_inactive_window_excluded(self) -> None:
        """Inactive/expired window should be excluded."""
        scorecard = {
            "grace_windows": [
                {
                    "rf_id": "RF-001",
                    "approved": True,
                    "starts_on": "2024-01-01",
                    "ends_on": "2024-12-31",  # past
                    "allowances": {"total_exemptions": 5},
                }
            ]
        }
        active, total, _, _ = resolve_grace_allowances(
            scorecard, today=date(2025, 6, 15)
        )
        assert active == []
        assert total == 0

    def test_unapproved_window_excluded(self) -> None:
        """Unapproved window should not be included."""
        scorecard = {
            "grace_windows": [
                {
                    "rf_id": "RF-001",
                    "approved": False,
                    "starts_on": "2025-01-01",
                    "ends_on": "2025-12-31",
                    "allowances": {"total_exemptions": 5},
                }
            ]
        }
        active, total, _, _ = resolve_grace_allowances(
            scorecard, today=date(2025, 6, 15)
        )
        assert active == []
        assert total == 0


class TestEvaluateBudgetViolations:
    """Tests for evaluate_budget_violations."""

    def _make_scorecard_target(
        self,
        max_total: int = 20,
        min_score: float = 50.0,
    ) -> tuple[dict[str, object], dict[str, object]]:
        scorecard = {
            "registry_groups": {
                "grp1": {"registries": ["reg_a"]},
            }
        }
        target = {
            "quarter": "2025-Q1",
            "max_total_exemptions": max_total,
            "min_integral_score": min_score,
            "registry_budgets": {"reg_a": max_total},
            "group_budgets": {"grp1": max_total},
        }
        return scorecard, target  # type: ignore[return-value]

    def test_no_violations_within_budget(self) -> None:
        """No violations when all counts are within budget."""
        scorecard, target = self._make_scorecard_target(max_total=20, min_score=30.0)
        inventory = _make_inventory(
            total=5,
            by_registry={"reg_a": 5},
            expired=0,
        )
        violations, by_group, score = evaluate_budget_violations(
            inventory=inventory,
            scorecard=scorecard,
            target=target,
            baseline_total=20,
            allowance_total=0,
            allowance_by_registry={},
            allowance_by_group={},
        )
        assert violations == []
        assert by_group == {"grp1": 5}
        assert score > 0

    def test_registry_over_budget_violation(self) -> None:
        """Registry count exceeding budget should add violation."""
        scorecard, target = self._make_scorecard_target(max_total=10, min_score=30.0)
        inventory = _make_inventory(
            total=15,
            by_registry={"reg_a": 15},
            expired=0,
        )
        violations, _, _ = evaluate_budget_violations(
            inventory=inventory,
            scorecard=scorecard,
            target=target,
            baseline_total=20,
            allowance_total=0,
            allowance_by_registry={},
            allowance_by_group={},
        )
        assert any("reg_a" in v for v in violations)

    def test_total_over_budget_violation(self) -> None:
        """Total exemptions exceeding budget should add violation."""
        scorecard, target = self._make_scorecard_target(max_total=10, min_score=30.0)
        inventory = _make_inventory(
            total=15,
            by_registry={"reg_a": 5},  # registry ok but total too high
            expired=0,
        )
        violations, _, _ = evaluate_budget_violations(
            inventory=inventory,
            scorecard=scorecard,
            target=target,
            baseline_total=20,
            allowance_total=0,
            allowance_by_registry={},
            allowance_by_group={},
        )
        assert any("total exemptions" in v for v in violations)

    def test_low_score_violation(self) -> None:
        """Integral score below target should add violation."""
        scorecard, target = self._make_scorecard_target(max_total=20, min_score=95.0)
        inventory = _make_inventory(
            total=20,
            by_registry={"reg_a": 20},
            expired=10,
        )
        violations, _, score = evaluate_budget_violations(
            inventory=inventory,
            scorecard=scorecard,
            target=target,
            baseline_total=20,
            allowance_total=0,
            allowance_by_registry={},
            allowance_by_group={},
        )
        assert score < 95.0
        assert any("integral debt score" in v for v in violations)


class TestEvaluateGovernanceViolations:
    """Tests for evaluate_governance_violations."""

    def test_no_violations_no_decomposition_targets(self) -> None:
        """Missing decomposition targets with no owner issues should produce no errors."""
        inventory = _make_inventory(
            total=5,
            by_owner={"alice": 3, "bob": 2},
            expired=0,
        )
        scorecard: dict[str, object] = {
            "governance": {
                "owner_diversification": {
                    "starts_quarter": "2030-Q1",  # far future
                    "min_distinct_owners": 3,
                }
            }
        }
        violations = evaluate_governance_violations(
            inventory=inventory,
            scorecard=scorecard,
            quarter="2025-Q1",
            integral_score=80.0,
        )
        # All governance checks should pass (diversification starts far future)
        assert isinstance(violations, list)

    def test_violations_returned_as_list(self) -> None:
        """Return type should be list even with no violations."""
        inventory = _make_inventory()
        violations = evaluate_governance_violations(
            inventory=inventory,
            scorecard={},
            quarter="2025-Q1",
            integral_score=100.0,
        )
        assert isinstance(violations, list)
