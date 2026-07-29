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
"""Unit tests for debt_scorecard_validation module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quality.debt_scorecard_validation import (
    validate_debt_scorecard_structure,
)


pytestmark = pytest.mark.unit


def _minimal_valid_scorecard() -> dict[str, object]:
    """Build a minimal valid scorecard for testing."""
    return {
        "schema_version": 1,
        "baseline": {
            "total_exemptions": 10,
            "by_registry": {"reg_a": 6, "reg_b": 4},
        },
        "historical_baseline": {
            "total_exemptions": 12,
            "by_registry": {"reg_a": 7, "reg_b": 5},
            "snapshot_date": "2025-01-01",
            "source_report": "reports/quality/historical-baseline.json",
        },
        "registry_groups": {
            "grp1": {"registries": ["reg_a"]},
            "grp2": {"registries": ["reg_b"]},
        },
        "governance": {
            "baseline_policy": {
                "enforceable_section": "baseline",
                "historical_section": "historical_baseline",
                "registry_sync_source": "baseline",
                "rationale": "Keep enforceable and historical baselines distinct.",
            },
            "review_policy": {
                "new_exemption_requires": [
                    "owner",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "owner_registry_q3_subsystems": {
                "sub_a": {"owner": "alice"},
                "sub_b": {"owner": "bob"},
                "sub_c": {"owner": "carol"},
            },
            "growth_gate_default_mode": "block",
            "allow_grace_windows_only_for_rf": False,
            "owner_diversification": {
                "starts_quarter": "2025-Q1",
                "min_distinct_owners": 2,
            },
            "growth_section_gate_rollout": {
                "default_mode": "block",
                "warn_until_by_section": {},
            },
            "burn_down_priorities": {
                "registries": ["reg_a"],
            },
        },
        "quarterly_targets": [
            {
                "quarter": "2025-Q1",
                "max_total_exemptions": 20,
                "min_integral_score": 50.0,
                "group_budgets": {"grp1": 12, "grp2": 8},
                "registry_budgets": {"reg_a": 12, "reg_b": 8},
            },
            {
                "quarter": "2025-Q2",
                "max_total_exemptions": 15,
                "min_integral_score": 60.0,
                "group_budgets": {"grp1": 9, "grp2": 6},
                "registry_budgets": {"reg_a": 9, "reg_b": 6},
            },
        ],
        "hotspot_budgets": [
            {
                "name": "hotspot_a",
                "rationale": "Track reg_a debt in one concrete source subtree.",
                "path_prefixes": ["src/bioetl/application/composite/"],
                "registry_budgets": {"reg_a": 6},
            },
            {
                "name": "hotspot_b",
                "rationale": "Track reg_b debt in one concrete source subtree.",
                "path_prefixes": ["src/bioetl/infrastructure/storage/"],
                "registry_budgets": {"reg_b": 4},
            },
        ],
        "owner_decomposition_targets": [
            {
                "quarter": "2025-Q1",
                "allocations": {"alice": 10, "bob": 10},
            },
            {
                "quarter": "2025-Q2",
                "allocations": {"alice": 8, "bob": 7},
            },
        ],
        "expiry_decomposition_targets": [
            {"quarter": "2025-Q1", "max_entries_expiring_in_quarter": 8},
            {"quarter": "2025-Q2", "max_entries_expiring_in_quarter": 5},
        ],
        "program_done_criteria": {
            "max_total_exemptions": 0,
            "min_integral_score": 95.0,
            "max_expired_entries": 0,
            "deadline_quarter": "2026-Q4",
        },
        "grace_windows": [],
    }


class TestValidateDebtScorecardStructure:
    """Tests for validate_debt_scorecard_structure."""

    def test_scorecard_structure__scorecard_no_errors__0048c8a0(self) -> None:
        """A fully valid scorecard should produce no errors."""
        raw = _minimal_valid_scorecard()
        errors = validate_debt_scorecard_structure(raw)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_wrong_schema_version(self) -> None:
        """Wrong schema_version should add error."""
        raw = _minimal_valid_scorecard()
        raw["schema_version"] = 2
        errors = validate_debt_scorecard_structure(raw)
        assert any("schema_version" in e for e in errors)

    def test_missing_schema_version(self) -> None:
        """Missing schema_version should add error."""
        raw = _minimal_valid_scorecard()
        del raw["schema_version"]  # type: ignore[attr-defined]
        errors = validate_debt_scorecard_structure(raw)
        assert any("schema_version" in e for e in errors)

    def test_missing_baseline(self) -> None:
        """Missing baseline should return early with error."""
        raw = _minimal_valid_scorecard()
        del raw["baseline"]  # type: ignore[attr-defined]
        errors = validate_debt_scorecard_structure(raw)
        assert any("baseline" in e for e in errors)

    def test_scorecard_structure__registry_groups__0b4ae76f(self) -> None:
        """Missing registry_groups should return early with error."""
        raw = _minimal_valid_scorecard()
        del raw["registry_groups"]  # type: ignore[attr-defined]
        errors = validate_debt_scorecard_structure(raw)
        assert any("registry_groups" in e for e in errors)

    def test_missing_governance(self) -> None:
        """Missing governance section should add error."""
        raw = _minimal_valid_scorecard()
        del raw["governance"]  # type: ignore[attr-defined]
        errors = validate_debt_scorecard_structure(raw)
        assert any("governance" in e for e in errors)

    def test_missing_quarterly_targets(self) -> None:
        """Missing quarterly_targets should add error."""
        raw = _minimal_valid_scorecard()
        del raw["quarterly_targets"]  # type: ignore[attr-defined]
        errors = validate_debt_scorecard_structure(raw)
        assert any("quarterly_targets" in e for e in errors)

    def test_non_decreasing_max_exemptions(self) -> None:
        """Non-decreasing max_total_exemptions should add error."""
        raw = _minimal_valid_scorecard()
        assert isinstance(raw["quarterly_targets"], list)
        raw["quarterly_targets"][1]["max_total_exemptions"] = 25  # type: ignore[index]
        errors = validate_debt_scorecard_structure(raw)
        assert any(
            "max_total_exemptions" in e and "strictly decrease" in e for e in errors
        )

    def test_non_increasing_min_score(self) -> None:
        """Non-increasing min_integral_score should add error."""
        raw = _minimal_valid_scorecard()
        assert isinstance(raw["quarterly_targets"], list)
        raw["quarterly_targets"][1]["min_integral_score"] = 40.0  # type: ignore[index]
        errors = validate_debt_scorecard_structure(raw)
        assert any(
            "min_integral_score" in e and "strictly increase" in e for e in errors
        )

    def test_invalid_program_done_deadline(self) -> None:
        """Invalid deadline_quarter in program_done_criteria should add error."""
        raw = _minimal_valid_scorecard()
        assert isinstance(raw["program_done_criteria"], dict)
        raw["program_done_criteria"]["deadline_quarter"] = "not-a-quarter"  # type: ignore[index]
        errors = validate_debt_scorecard_structure(raw)
        assert any("deadline_quarter" in e for e in errors)

    def test_returns_list(self) -> None:
        """Should always return a list."""
        errors = validate_debt_scorecard_structure({})
        assert isinstance(errors, list)
