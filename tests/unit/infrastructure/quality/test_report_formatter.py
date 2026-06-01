"""Unit tests for report_formatter module."""

from __future__ import annotations

from collections import Counter
from datetime import date

import pytest

from bioetl.infrastructure.quality.report_formatter import (
    _collect_allowances,
    _extract_growth_violation_section,
    _is_active_grace_window,
    _is_rollout_cutoff_active,
    _is_rollout_cutoff_stale,
    _resolve_rollout_mode_for_section,
    split_growth_violations_by_severity,
)

pytestmark = pytest.mark.unit


class TestIsActiveGraceWindow:
    """Tests for _is_active_grace_window."""

    def test_active_window(self) -> None:
        """Window that includes today should be active."""
        window = {
            "approved": True,
            "starts_on": "2025-01-01",
            "ends_on": "2025-12-31",
        }
        assert _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_window_starts_today(self) -> None:
        """Window starting today should be active."""
        window = {
            "approved": True,
            "starts_on": "2025-06-15",
            "ends_on": "2025-12-31",
        }
        assert _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_window_ends_today(self) -> None:
        """Window ending today should be active."""
        window = {
            "approved": True,
            "starts_on": "2025-01-01",
            "ends_on": "2025-06-15",
        }
        assert _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_future_window(self) -> None:
        """Window starting in the future should not be active."""
        window = {
            "approved": True,
            "starts_on": "2026-01-01",
            "ends_on": "2026-12-31",
        }
        assert not _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_past_window(self) -> None:
        """Window that has already ended should not be active."""
        window = {
            "approved": True,
            "starts_on": "2024-01-01",
            "ends_on": "2024-12-31",
        }
        assert not _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_not_approved(self) -> None:
        """Unapproved window should not be active."""
        window = {
            "approved": False,
            "starts_on": "2025-01-01",
            "ends_on": "2025-12-31",
        }
        assert not _is_active_grace_window(window, today=date(2025, 6, 15))

    def test_is_active_grace_window__not_dict__46d5c5ef(self) -> None:
        """Non-dict window should not be active."""
        assert not _is_active_grace_window("invalid", today=date(2025, 6, 15))

    def test_is_active_grace_window__invalid_dates__c7d62eb3(self) -> None:
        """Window with invalid date strings should not be active."""
        window = {
            "approved": True,
            "starts_on": "not-a-date",
            "ends_on": "also-bad",
        }
        assert not _is_active_grace_window(window, today=date(2025, 6, 15))


class TestCollectAllowances:
    """Tests for _collect_allowances."""

    def test_single_window_all_allowances(self) -> None:
        """Should correctly aggregate all allowance fields."""
        windows = [
            {
                "allowances": {
                    "total_exemptions": 5,
                    "registry_budgets": {"reg_a": 3},
                    "group_budgets": {"grp1": 2},
                }
            }
        ]
        total, by_registry, by_group = _collect_allowances(windows)
        assert total == 5
        assert by_registry["reg_a"] == 3
        assert by_group["grp1"] == 2

    def test_multiple_windows_aggregated(self) -> None:
        """Should aggregate across multiple active windows."""
        windows = [
            {
                "allowances": {
                    "total_exemptions": 3,
                    "registry_budgets": {"reg_a": 2},
                }
            },
            {
                "allowances": {
                    "total_exemptions": 4,
                    "registry_budgets": {"reg_a": 1},
                }
            },
        ]
        total, by_registry, _ = _collect_allowances(windows)
        assert total == 7
        assert by_registry["reg_a"] == 3

    def test_empty_windows(self) -> None:
        """Empty list should return zeros and empty counters."""
        total, by_registry, by_group = _collect_allowances([])
        assert total == 0
        assert by_registry == Counter()
        assert by_group == Counter()

    def test_window_without_allowances(self) -> None:
        """Window without 'allowances' key should be skipped."""
        windows = [{"rf_id": "RF-001"}]
        total, _, _ = _collect_allowances(windows)
        assert total == 0

    def test_non_dict_allowances_skipped(self) -> None:
        """Non-dict allowances should be skipped."""
        windows = [{"allowances": "invalid"}]
        total, _by_registry, _by_group = _collect_allowances(windows)
        assert total == 0

    def test_non_int_values_skipped(self) -> None:
        """Non-int registry/group budget values should be skipped."""
        windows = [
            {
                "allowances": {
                    "total_exemptions": 5,
                    "registry_budgets": {"reg_a": "not_int"},
                    "group_budgets": {"grp1": "also_not_int"},
                }
            }
        ]
        total, by_registry, by_group = _collect_allowances(windows)
        assert total == 5
        assert "reg_a" not in by_registry
        assert "grp1" not in by_group


class TestRolloutCutoffHelpers:
    """Tests for rollout cutoff helper predicates."""

    def test_active_cutoff_in_future_returns_true(self) -> None:
        assert _is_rollout_cutoff_active("2026-12-31", today=date(2026, 3, 16))

    def test_stale_cutoff_in_past_returns_true(self) -> None:
        assert _is_rollout_cutoff_stale("2026-03-01", today=date(2026, 3, 16))


class TestExtractGrowthViolationSection:
    """Tests for _extract_growth_violation_section."""

    def test_registry_violation(self) -> None:
        """Should extract registry name from registry violation."""
        result = _extract_growth_violation_section(
            "registry 'reg_a' count 15 exceeds budget 10"
        )
        assert result == "registry:reg_a"

    def test_group_violation(self) -> None:
        """Should extract group name from group violation."""
        result = _extract_growth_violation_section(
            "group 'grp1' count 20 exceeds budget 15"
        )
        assert result == "group:grp1"

    def test_total_violation(self) -> None:
        """Should return 'total_exemptions' for total violation."""
        result = _extract_growth_violation_section(
            "total exemptions 100 exceeds budget 90"
        )
        assert result == "total_exemptions"

    def test_integral_score_violation(self) -> None:
        """Should return 'integral_score' for score violation."""
        result = _extract_growth_violation_section(
            "integral debt score 40.5 is below target 80.0"
        )
        assert result == "integral_score"

    def test_unknown_violation(self) -> None:
        """Unknown violation format should return 'unknown'."""
        result = _extract_growth_violation_section("some random violation message")
        assert result == "unknown"


class TestResolveRolloutModeForSection:
    """Tests for _resolve_rollout_mode_for_section."""

    def test_no_governance_returns_fallback(self) -> None:
        """Missing governance should return fallback_mode."""
        result = _resolve_rollout_mode_for_section(
            scorecard={},
            section_key="registry:reg_a",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "block"

    def test_warn_until_in_future_returns_warn(self) -> None:
        """section in warn_until_by_section with future cutoff should return 'warn'."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "registry:reg_a": "2025-12-31",
                    },
                }
            }
        }
        result = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key="registry:reg_a",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "warn"

    def test_warn_until_in_past_returns_default(self) -> None:
        """Expired warn_until cutoff should return default_mode."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "registry:reg_a": "2024-01-01",  # past
                    },
                }
            }
        }
        result = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key="registry:reg_a",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "block"

    def test_wildcard_key_applies(self) -> None:
        """Wildcard '*' key should apply to all sections."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "*": "2025-12-31",
                    },
                }
            }
        }
        result = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key="group:grp1",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "warn"

    def test_type_wildcard_applies(self) -> None:
        """Type wildcard like 'registry:*' should match 'registry:anything'."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "registry:*": "2025-12-31",
                    },
                }
            }
        }
        result = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key="registry:reg_a",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "warn"

    def test_default_mode_from_rollout(self) -> None:
        """default_mode in rollout should override fallback."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "warn",
                    "warn_until_by_section": {},
                }
            }
        }
        result = _resolve_rollout_mode_for_section(
            scorecard=scorecard,
            section_key="unknown",
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert result == "warn"


class TestSplitGrowthViolationsBySeverity:
    """Tests for split_growth_violations_by_severity."""

    def test_all_blocking_by_default(self) -> None:
        """Without rollout policy, all violations should be blocking."""
        violations = [
            "registry 'reg_a' count 15 exceeds budget 10",
            "total exemptions 100 exceeds budget 90",
        ]
        blocking, warning = split_growth_violations_by_severity(
            violations=violations,
            scorecard={},
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert len(blocking) == 2
        assert warning == []

    def test_warn_mode_splits_violations(self) -> None:
        """Violations in warn period should be separated from blocking."""
        scorecard = {
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "*": "2025-12-31",  # all sections in warn period
                    },
                }
            }
        }
        violations = [
            "registry 'reg_a' count 15 exceeds budget 10",
            "total exemptions 100 exceeds budget 90",
        ]
        blocking, warning = split_growth_violations_by_severity(
            violations=violations,
            scorecard=scorecard,
            today=date(2025, 6, 15),
            fallback_mode="block",
        )
        assert blocking == []
        assert len(warning) == 2

    def test_empty_violations(self) -> None:
        """Empty violations should return empty lists."""
        blocking, warning = split_growth_violations_by_severity(
            violations=[],
            scorecard={},
            today=date(2025, 6, 15),
        )
        assert blocking == []
        assert warning == []

    def test_fallback_warn_mode(self) -> None:
        """fallback_mode='warn' should route all violations to warnings."""
        violations = ["total exemptions 100 exceeds budget 90"]
        blocking, warning = split_growth_violations_by_severity(
            violations=violations,
            scorecard={},
            today=date(2025, 6, 15),
            fallback_mode="warn",
        )
        assert blocking == []
        assert len(warning) == 1

    def test_invalid_fallback_mode_defaults_to_block(self) -> None:
        """Invalid fallback_mode should default to 'block'."""
        violations = ["total exemptions 100 exceeds budget 90"]
        blocking, warning = split_growth_violations_by_severity(
            violations=violations,
            scorecard={},
            today=date(2025, 6, 15),
            fallback_mode="invalid",
        )
        assert len(blocking) == 1
        assert warning == []

    def test_violations_by_severity__to_date_today__ada5acb6(self) -> None:
        """today=None should use date.today() without error."""
        blocking, warning = split_growth_violations_by_severity(
            violations=[],
            scorecard={},
        )
        assert blocking == []
        assert warning == []
