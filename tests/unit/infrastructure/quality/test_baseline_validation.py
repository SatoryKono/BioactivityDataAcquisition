"""Unit tests for _baseline_validation module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quality._baseline_validation import (
    _is_valid_rollout_section_key,
    _validate_baseline_section,
    _validate_historical_baseline_section,
    _validate_registry_group_entry,
    _validate_registry_groups_section,
)

pytestmark = pytest.mark.unit


class TestValidateBaselineSection:
    """Tests for _validate_baseline_section."""

    def test_valid_baseline(self) -> None:
        """Valid baseline section should return parsed values."""
        raw = {
            "baseline": {
                "total_exemptions": 10,
                "by_registry": {"reg_a": 6, "reg_b": 4},
            }
        }
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        assert result is not None
        total, by_registry = result
        assert total == 10
        assert by_registry == {"reg_a": 6, "reg_b": 4}
        assert errors == []

    def test_missing_baseline_key(self) -> None:
        """Missing baseline key should add error and return None."""
        errors: list[str] = []
        result = _validate_baseline_section({}, errors)
        assert result is None
        assert any("baseline" in e for e in errors)

    def test_baseline_not_dict(self) -> None:
        """Baseline that is not a dict should add error and return None."""
        errors: list[str] = []
        result = _validate_baseline_section({"baseline": "invalid"}, errors)
        assert result is None
        assert any("baseline" in e for e in errors)

    def test_missing_by_registry(self) -> None:
        """Missing by_registry key should add error and return None."""
        raw = {"baseline": {"total_exemptions": 5}}
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        assert result is None
        assert any("by_registry" in e for e in errors)

    def test_empty_by_registry(self) -> None:
        """Empty by_registry should add error and return None."""
        raw = {"baseline": {"total_exemptions": 0, "by_registry": {}}}
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        assert result is None
        assert any("by_registry" in e for e in errors)

    def test_total_mismatch(self) -> None:
        """Total mismatch should add error but still return values."""
        raw = {
            "baseline": {
                "total_exemptions": 99,
                "by_registry": {"reg_a": 5, "reg_b": 3},
            }
        }
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        assert result is not None
        assert any("total_exemptions" in e for e in errors)

    def test_invalid_registry_name(self) -> None:
        """Non-string registry name should add error and skip entry."""
        raw = {
            "baseline": {
                "total_exemptions": 5,
                "by_registry": {"valid": 5, "": 0},
            }
        }
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        assert result is not None
        assert any("registry name" in e for e in errors)

    def test_negative_count_in_registry(self) -> None:
        """Negative count in by_registry should add error."""
        raw = {
            "baseline": {
                "total_exemptions": 5,
                "by_registry": {"reg_a": -1},
            }
        }
        errors: list[str] = []
        _validate_baseline_section(raw, errors)
        assert any("non-negative" in e for e in errors)

    def test_total_none_is_allowed(self) -> None:
        """Missing total_exemptions is a validation error but doesn't break result."""
        raw = {
            "baseline": {
                "by_registry": {"reg_a": 5},
            }
        }
        errors: list[str] = []
        result = _validate_baseline_section(raw, errors)
        # Returns result with None total; errors for total
        assert result is not None


class TestValidateRegistryGroupEntry:
    """Tests for _validate_registry_group_entry."""

    def test_valid_entry(self) -> None:
        """Valid group entry should return tuple of registry names."""
        errors: list[str] = []
        result = _validate_registry_group_entry(
            group_name="grp1",
            group_data={"registries": ["reg_a", "reg_b"]},
            errors=errors,
        )
        assert result == ("reg_a", "reg_b")
        assert errors == []

    def test_not_dict(self) -> None:
        """Non-dict group_data should add error and return None."""
        errors: list[str] = []
        result = _validate_registry_group_entry(
            group_name="grp1",
            group_data="invalid",
            errors=errors,
        )
        assert result is None
        assert len(errors) == 1

    def test_missing_registries(self) -> None:
        """Missing registries key should add error and return None."""
        errors: list[str] = []
        result = _validate_registry_group_entry(
            group_name="grp1",
            group_data={},
            errors=errors,
        )
        assert result is None
        assert any("registries" in e for e in errors)

    def test_empty_registries_list(self) -> None:
        """Empty registries list should add error and return None."""
        errors: list[str] = []
        result = _validate_registry_group_entry(
            group_name="grp1",
            group_data={"registries": []},
            errors=errors,
        )
        assert result is None

    def test_invalid_registry_item(self) -> None:
        """Invalid registry items (non-string or empty) are skipped with error."""
        errors: list[str] = []
        result = _validate_registry_group_entry(
            group_name="grp1",
            group_data={"registries": ["valid", "", 42]},
            errors=errors,
        )
        # valid items are kept
        assert result is not None
        assert "valid" in result
        assert len(errors) >= 2  # empty string and int both cause errors


class TestValidateHistoricalBaselineSection:
    """Tests for _validate_historical_baseline_section."""

    def test_valid_historical_baseline(self) -> None:
        """Historical baseline with matching metadata and floors should pass."""
        raw = {
            "historical_baseline": {
                "total_exemptions": 12,
                "by_registry": {"reg_a": 7, "reg_b": 5},
                "snapshot_date": "2026-03-01",
                "source_report": "reports/example.md",
            }
        }
        errors: list[str] = []

        result = _validate_historical_baseline_section(
            raw,
            enforceable_total=10,
            enforceable_registry_counts={"reg_a": 6, "reg_b": 4},
            errors=errors,
        )

        assert result is not None
        assert errors == []

    def test_missing_and_extra_registries_are_reported(self) -> None:
        """Historical baseline should report registry-set drift against baseline."""
        raw = {
            "historical_baseline": {
                "total_exemptions": 12,
                "by_registry": {"reg_a": 7, "reg_extra": 5},
                "snapshot_date": "2026-03-01",
                "source_report": "reports/example.md",
            }
        }
        errors: list[str] = []

        _validate_historical_baseline_section(
            raw,
            enforceable_total=10,
            enforceable_registry_counts={"reg_a": 6, "reg_b": 4},
            errors=errors,
        )

        assert any("missing enforceable registries" in e for e in errors)
        assert any("not present in baseline" in e for e in errors)

    def test_historical_totals_and_registry_counts_cannot_drop_below_baseline(
        self,
    ) -> None:
        """Historical baseline must not go below enforceable totals or registry counts."""
        raw = {
            "historical_baseline": {
                "total_exemptions": 9,
                "by_registry": {"reg_a": 5, "reg_b": 4},
                "snapshot_date": "2026-03-01",
                "source_report": "reports/example.md",
            }
        }
        errors: list[str] = []

        _validate_historical_baseline_section(
            raw,
            enforceable_total=10,
            enforceable_registry_counts={"reg_a": 6, "reg_b": 4},
            errors=errors,
        )

        assert any(
            "total_exemptions must be greater than or equal" in e for e in errors
        )
        assert any("historical_baseline.by_registry.reg_a" in e for e in errors)


class TestValidateRegistryGroupsSection:
    """Tests for _validate_registry_groups_section."""

    def test_valid_groups(self) -> None:
        """Valid groups section should return normalized groups dict."""
        raw = {
            "registry_groups": {
                "grp1": {"registries": ["reg_a"]},
                "grp2": {"registries": ["reg_b"]},
            }
        }
        errors: list[str] = []
        result = _validate_registry_groups_section(
            raw,
            baseline_registry_names={"reg_a", "reg_b"},
            errors=errors,
        )
        assert "grp1" in result
        assert "grp2" in result
        assert errors == []

    def test_missing_registry_groups(self) -> None:
        """Missing registry_groups should add error and return empty dict."""
        errors: list[str] = []
        result = _validate_registry_groups_section(
            {},
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result == {}
        assert any("registry_groups" in e for e in errors)

    def test_not_dict(self) -> None:
        """Non-dict registry_groups should add error."""
        errors: list[str] = []
        result = _validate_registry_groups_section(
            {"registry_groups": "invalid"},
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result == {}
        assert len(errors) >= 1

    def test_duplicate_registries_across_groups(self) -> None:
        """Registries in multiple groups should add error."""
        raw = {
            "registry_groups": {
                "grp1": {"registries": ["reg_a"]},
                "grp2": {"registries": ["reg_a"]},  # duplicate
            }
        }
        errors: list[str] = []
        _validate_registry_groups_section(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert any("multiple groups" in e for e in errors)

    def test_missing_baseline_registries_in_groups(self) -> None:
        """Registries in baseline but not in any group should add error."""
        raw = {
            "registry_groups": {
                "grp1": {"registries": ["reg_a"]},
            }
        }
        errors: list[str] = []
        _validate_registry_groups_section(
            raw,
            baseline_registry_names={"reg_a", "reg_b"},  # reg_b not in any group
            errors=errors,
        )
        assert any("missing" in e for e in errors)

    def test_extra_registries_not_in_baseline(self) -> None:
        """Registries in groups but not in baseline should add error."""
        raw = {
            "registry_groups": {
                "grp1": {"registries": ["reg_a", "reg_unknown"]},
            }
        }
        errors: list[str] = []
        _validate_registry_groups_section(
            raw,
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert any("unknown" in e for e in errors)


class TestIsValidRolloutSectionKey:
    """Tests for _is_valid_rollout_section_key."""

    def test_wildcard(self) -> None:
        """'*' should always be valid."""
        assert _is_valid_rollout_section_key(
            key="*",
            baseline_registry_names=set(),
            group_names=set(),
        )

    def test_total_exemptions(self) -> None:
        """'total_exemptions' should be valid."""
        assert _is_valid_rollout_section_key(
            key="total_exemptions",
            baseline_registry_names=set(),
            group_names=set(),
        )

    def test_integral_score(self) -> None:
        """'integral_score' should be valid."""
        assert _is_valid_rollout_section_key(
            key="integral_score",
            baseline_registry_names=set(),
            group_names=set(),
        )

    def test_registry_wildcard(self) -> None:
        """'registry:*' should be valid."""
        assert _is_valid_rollout_section_key(
            key="registry:*",
            baseline_registry_names=set(),
            group_names=set(),
        )

    def test_registry_known_name(self) -> None:
        """'registry:<known>' should be valid."""
        assert _is_valid_rollout_section_key(
            key="registry:reg_a",
            baseline_registry_names={"reg_a"},
            group_names=set(),
        )

    def test_registry_unknown_name(self) -> None:
        """'registry:<unknown>' should be invalid."""
        assert not _is_valid_rollout_section_key(
            key="registry:unknown_reg",
            baseline_registry_names={"reg_a"},
            group_names=set(),
        )

    def test_group_wildcard(self) -> None:
        """'group:*' should be valid."""
        assert _is_valid_rollout_section_key(
            key="group:*",
            baseline_registry_names=set(),
            group_names=set(),
        )

    def test_group_known_name(self) -> None:
        """'group:<known>' should be valid."""
        assert _is_valid_rollout_section_key(
            key="group:grp1",
            baseline_registry_names=set(),
            group_names={"grp1"},
        )

    def test_group_unknown_name(self) -> None:
        """'group:<unknown>' should be invalid."""
        assert not _is_valid_rollout_section_key(
            key="group:unknown_grp",
            baseline_registry_names=set(),
            group_names={"grp1"},
        )

    def test_unknown_key(self) -> None:
        """Completely unknown keys should be invalid."""
        assert not _is_valid_rollout_section_key(
            key="something_else",
            baseline_registry_names=set(),
            group_names=set(),
        )
