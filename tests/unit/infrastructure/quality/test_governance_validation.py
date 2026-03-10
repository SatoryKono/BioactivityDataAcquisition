"""Unit tests for _governance_validation module."""

from __future__ import annotations

from bioetl.infrastructure.quality._governance_validation import (
    _validate_governance_section,
    _validate_growth_rollout,
    _validate_owner_registry_subsystems,
    _validate_review_policy,
    _validate_warn_until_by_section,
)


class TestValidateReviewPolicy:
    """Tests for _validate_review_policy."""

    def test_valid_policy(self) -> None:
        """Valid policy should produce no errors."""
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": ["owner", "expires_on", "removal_step"]},
            errors=errors,
        )
        assert errors == []

    def test_not_dict(self) -> None:
        """Non-dict review_policy should add error."""
        errors: list[str] = []
        _validate_review_policy("invalid", errors=errors)
        assert any("review_policy" in e for e in errors)

    def test_missing_new_exemption_requires(self) -> None:
        """Missing new_exemption_requires should add error."""
        errors: list[str] = []
        _validate_review_policy({}, errors=errors)
        assert any("new_exemption_requires" in e for e in errors)

    def test_empty_list(self) -> None:
        """Empty new_exemption_requires list should add error."""
        errors: list[str] = []
        _validate_review_policy({"new_exemption_requires": []}, errors=errors)
        assert any("new_exemption_requires" in e for e in errors)

    def test_not_list(self) -> None:
        """Non-list new_exemption_requires should add error."""
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": "owner"},
            errors=errors,
        )
        assert any("new_exemption_requires" in e for e in errors)

    def test_missing_owner_field(self) -> None:
        """Missing required 'owner' field should add error."""
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": ["expires_on", "removal_step"]},
            errors=errors,
        )
        assert any("'owner'" in e for e in errors)

    def test_missing_expires_on_field(self) -> None:
        """Missing required 'expires_on' field should add error."""
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": ["owner", "removal_step"]},
            errors=errors,
        )
        assert any("'expires_on'" in e for e in errors)

    def test_missing_removal_step_field(self) -> None:
        """Missing required 'removal_step' field should add error."""
        errors: list[str] = []
        _validate_review_policy(
            {"new_exemption_requires": ["owner", "expires_on"]},
            errors=errors,
        )
        assert any("'removal_step'" in e for e in errors)

    def test_whitespace_stripped(self) -> None:
        """Fields with whitespace should be stripped before comparison."""
        errors: list[str] = []
        _validate_review_policy(
            {
                "new_exemption_requires": [
                    "  owner  ",
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
        """Valid subsystems with 3+ should produce no errors."""
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

    def test_not_dict(self) -> None:
        """Non-dict subsystems should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems("invalid", errors=errors)
        assert any("expected mapping" in e for e in errors)

    def test_fewer_than_3_subsystems(self) -> None:
        """Less than 3 subsystems should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {"sub_a": {"owner": "alice"}, "sub_b": {"owner": "bob"}},
            errors=errors,
        )
        assert any("at least 3 subsystems" in e for e in errors)

    def test_fewer_than_3_distinct_owners(self) -> None:
        """Less than 3 distinct owners should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "sub_a": {"owner": "alice"},
                "sub_b": {"owner": "alice"},
                "sub_c": {"owner": "alice"},
            },
            errors=errors,
        )
        assert any("at least 3 distinct owners" in e for e in errors)

    def test_empty_subsystem_key(self) -> None:
        """Empty subsystem key should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "": {"owner": "alice"},
                "sub_b": {"owner": "bob"},
                "sub_c": {"owner": "carol"},
            },
            errors=errors,
        )
        assert any("non-empty string" in e for e in errors)

    def test_cfg_not_dict(self) -> None:
        """Non-dict subsystem config should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "sub_a": "not_a_dict",
                "sub_b": {"owner": "bob"},
                "sub_c": {"owner": "carol"},
            },
            errors=errors,
        )
        assert any("expected mapping" in e for e in errors)

    def test_missing_owner(self) -> None:
        """Missing or empty owner should add error."""
        errors: list[str] = []
        _validate_owner_registry_subsystems(
            {
                "sub_a": {},  # no owner key
                "sub_b": {"owner": "bob"},
                "sub_c": {"owner": "carol"},
            },
            errors=errors,
        )
        assert any("owner" in e for e in errors)


class TestValidateWarnUntilBySection:
    """Tests for _validate_warn_until_by_section."""

    def test_valid_warn_until(self) -> None:
        """Valid section keys with ISO dates should produce no errors."""
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"*": "2025-12-31"},
            baseline_registry_names={"reg_a"},
            group_names={"grp1"},
            errors=errors,
        )
        assert errors == []

    def test_not_dict(self) -> None:
        """Non-dict warn_until should add error."""
        errors: list[str] = []
        _validate_warn_until_by_section(
            "invalid",
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("expected mapping" in e for e in errors)

    def test_invalid_section_key(self) -> None:
        """Unknown section key should add error."""
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"unknown_key": "2025-12-31"},
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("unknown section key" in e for e in errors)

    def test_invalid_date_format(self) -> None:
        """Invalid cutoff date should add error."""
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"*": "not-a-date"},
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("ISO date" in e for e in errors)

    def test_empty_string_key(self) -> None:
        """Empty string section key should add error."""
        errors: list[str] = []
        _validate_warn_until_by_section(
            {"": "2025-12-31"},
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("non-empty string" in e for e in errors)


class TestValidateGrowthRollout:
    """Tests for _validate_growth_rollout."""

    def test_valid_rollout(self) -> None:
        """Valid rollout section should produce no errors."""
        governance = {
            "growth_section_gate_rollout": {
                "default_mode": "warn",
                "warn_until_by_section": {},
            }
        }
        errors: list[str] = []
        _validate_growth_rollout(
            governance,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert errors == []

    def test_rollout_not_dict(self) -> None:
        """Non-dict rollout should add error."""
        governance = {"growth_section_gate_rollout": "invalid"}
        errors: list[str] = []
        _validate_growth_rollout(
            governance,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("expected mapping" in e for e in errors)

    def test_missing_rollout_uses_default(self) -> None:
        """Missing rollout section should use default mode without error."""
        governance: dict[str, object] = {}
        errors: list[str] = []
        _validate_growth_rollout(
            governance,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        # No error for missing rollout (uses empty dict fallback)
        assert not any("expected mapping" in e for e in errors)


class TestValidateGovernanceSection:
    """Tests for _validate_governance_section."""

    def _valid_raw(self) -> dict[str, object]:
        return {
            "governance": {
                "review_policy": {
                    "new_exemption_requires": ["owner", "expires_on", "removal_step"]
                },
                "owner_registry_q2_subsystems": {
                    "sub_a": {"owner": "alice"},
                    "sub_b": {"owner": "bob"},
                    "sub_c": {"owner": "carol"},
                },
                "growth_gate_default_mode": "block",
                "allow_grace_windows_only_for_rf": False,
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {},
                },
            }
        }

    def test_valid_governance(self) -> None:
        """Valid governance section should return True/False without errors."""
        raw = self._valid_raw()
        errors: list[str] = []
        result = _validate_governance_section(
            raw,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert isinstance(result, bool)
        assert result is False
        assert errors == []

    def test_missing_governance(self) -> None:
        """Missing governance should add error and return False."""
        errors: list[str] = []
        result = _validate_governance_section(
            {},
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert result is False
        assert any("governance" in e for e in errors)

    def test_governance_not_dict(self) -> None:
        """Non-dict governance should add error and return False."""
        errors: list[str] = []
        result = _validate_governance_section(
            {"governance": "invalid"},
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert result is False
        assert any("governance" in e for e in errors)

    def test_allow_rf_only_not_bool(self) -> None:
        """Non-bool allow_grace_windows_only_for_rf should add error."""
        raw = self._valid_raw()
        assert isinstance(raw["governance"], dict)
        raw["governance"]["allow_grace_windows_only_for_rf"] = "yes"  # type: ignore[index]
        errors: list[str] = []
        result = _validate_governance_section(
            raw,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert result is False
        assert any("allow_grace_windows_only_for_rf" in e for e in errors)

    def test_allow_rf_only_true_returned(self) -> None:
        """allow_grace_windows_only_for_rf=True should be returned."""
        raw = self._valid_raw()
        assert isinstance(raw["governance"], dict)
        raw["governance"]["allow_grace_windows_only_for_rf"] = True  # type: ignore[index]
        errors: list[str] = []
        result = _validate_governance_section(
            raw,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert result is True

    def test_invalid_growth_gate_mode(self) -> None:
        """Invalid growth_gate_default_mode should add error."""
        raw = self._valid_raw()
        assert isinstance(raw["governance"], dict)
        raw["governance"]["growth_gate_default_mode"] = "invalid_mode"  # type: ignore[index]
        errors: list[str] = []
        _validate_governance_section(
            raw,
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("gate" in e.lower() or "mode" in e.lower() for e in errors)
