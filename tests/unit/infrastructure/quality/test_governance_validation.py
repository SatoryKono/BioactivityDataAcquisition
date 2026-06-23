"""Unit tests for governance-section validation helpers."""

from __future__ import annotations

import pytest

from datetime import date

from bioetl.infrastructure.quality._governance_validation import (
    _validate_governance_section,
    _validate_growth_rollout,
    _validate_owner_registry_subsystems,
    _validate_review_policy,
    _validate_warn_until_by_section,
)


pytestmark = pytest.mark.unit


class TestValidateReviewPolicy:
    """Tests for _validate_review_policy."""

    def test_validate_review_policy__valid_policy__bad7babf(self) -> None:
        errors: list[str] = []
        _validate_review_policy(
            {
                "new_exemption_requires": [
                    "owner",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            errors=errors,
        )
        assert errors == []

    def test_missing_required_tracking_fields(self) -> None:
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": ["owner", "expires_on", "removal_step"]},
            errors=errors,
        )
        assert any("'classification'" in error for error in errors)
        assert any("'linked_rf'" in error for error in errors)

    def test_validate_review_policy__due_date_field__c9fb8292(self) -> None:
        errors: list[str] = []
        _validate_review_policy(
            {
                "new_exemption_requires": [
                    "owner",
                    "classification",
                    "linked_rf",
                    "removal_step",
                ]
            },
            errors=errors,
        )
        assert any("'expires_on'" in error for error in errors)

    def test_validate_review_policy__is_stripped__04bff0ba(self) -> None:
        errors: list[str] = []
        _validate_review_policy(
            {
                "new_exemption_requires": [
                    "  owner  ",
                    " classification ",
                    " linked_rf ",
                    " expires_on ",
                    " removal_step ",
                ]
            },
            errors=errors,
        )
        assert errors == []


class TestValidateOwnerRegistrySubsystems:
    """Tests for _validate_owner_registry_subsystems."""

    def test_valid_subsystems(self) -> None:
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "sub_a": {"owner": "alice"},
                "sub_b": {"owner": "bob"},
                "sub_c": {"owner": "carol"},
            },
            errors=errors,
        )
        assert errors == []

    def test_requires_three_distinct_owners(self) -> None:
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "sub_a": {"owner": "alice"},
                "sub_b": {"owner": "alice"},
                "sub_c": {"owner": "alice"},
            },
            errors=errors,
        )
        assert any("at least 3 distinct owners" in error for error in errors)


class TestValidateWarnUntilBySection:
    """Tests for _validate_warn_until_by_section."""

    def test_valid_rollout_map(self) -> None:
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"*": "2099-12-31", "registry:class_size": "2099-11-01"},
            baseline_registry_names={"class_size", "function_length"},
            group_names={"size_shape"},
            errors=errors,
            today=date(2026, 3, 16),
        )
        assert errors == []

    def test_invalid_section_key_is_rejected(self) -> None:
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"registry:unknown": "2025-12-31"},
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
        )
        assert any("unknown section key" in error for error in errors)

    def test_stale_cutoff_is_rejected(self) -> None:
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"registry:class_size": "2026-03-01"},
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
            today=date(2026, 3, 16),
        )
        assert any("stale cutoff date" in error for error in errors)


class TestValidateGrowthRollout:
    """Tests for _validate_growth_rollout."""

    def test_invalid_warn_until_date_is_reported(self) -> None:
        errors: list[str] = []
        _validate_growth_rollout(
            {
                "growth_gate_default_mode": "block",
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {"*": "not-a-date"},
                },
            },
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
        )
        assert any("expected ISO date" in error for error in errors)

    def test_stale_warn_until_date_is_reported(self) -> None:
        errors: list[str] = []
        _validate_growth_rollout(
            {
                "growth_gate_default_mode": "block",
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {"*": "2026-03-01"},
                },
            },
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
            today=date(2026, 3, 16),
        )
        assert any("stale cutoff date" in error for error in errors)


class TestValidateGovernanceSection:
    """Tests for _validate_governance_section."""

    def test_valid_governance_section_returns_flag(self) -> None:
        errors: list[str] = []
        allow_rf_only = _validate_governance_section(
            {
                "hotspot_budgets": [
                    {
                        "name": "storage_hotspot",
                        "rationale": "Track class_size debt in storage subtree.",
                        "path_prefixes": ["src/bioetl/infrastructure/storage/"],
                        "registry_budgets": {"class_size": 1},
                    }
                ],
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
                    "owner_registry_q2_subsystems": {
                        "sub_a": {"owner": "alice"},
                        "sub_b": {"owner": "bob"},
                        "sub_c": {"owner": "carol"},
                    },
                    "growth_gate_default_mode": "block",
                    "allow_grace_windows_only_for_rf": True,
                    "growth_section_gate_rollout": {
                        "default_mode": "block",
                        "warn_until_by_section": {"*": "2099-12-31"},
                    },
                },
            },
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
            today=date(2026, 3, 16),
        )
        assert errors == []
        assert allow_rf_only is True

    def test_invalid_grace_window_flag_is_reported(self) -> None:
        errors: list[str] = []
        allow_rf_only = _validate_governance_section(
            {
                "hotspot_budgets": [
                    {
                        "name": "storage_hotspot",
                        "rationale": "Track class_size debt in storage subtree.",
                        "path_prefixes": ["src/bioetl/infrastructure/storage/"],
                        "registry_budgets": {"class_size": 1},
                    }
                ],
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
                    "owner_registry_q2_subsystems": {
                        "sub_a": {"owner": "alice"},
                        "sub_b": {"owner": "bob"},
                        "sub_c": {"owner": "carol"},
                    },
                    "growth_gate_default_mode": "block",
                    "allow_grace_windows_only_for_rf": "yes",
                    "growth_section_gate_rollout": {
                        "default_mode": "block",
                        "warn_until_by_section": {"*": "2099-12-31"},
                    },
                },
            },
            baseline_registry_names={"class_size"},
            group_names={"size_shape"},
            errors=errors,
            today=date(2026, 3, 16),
        )
        assert allow_rf_only is False
        assert any("allow_grace_windows_only_for_rf" in error for error in errors)
