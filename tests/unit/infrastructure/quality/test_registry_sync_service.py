"""Unit tests for registry_sync_service module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quality.inventory import ExemptionInventorySummary
from bioetl.infrastructure.quality.registry_sync_service import (
    _validate_registry_baselines,
    _validate_registry_membership,
    _validate_total_exemptions,
    validate_registry_sync,
)


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


class TestValidateRegistryMembership:
    """Tests for _validate_registry_membership."""

    def test_matching_registries(self) -> None:
        """Identical live and baseline registries should produce no errors."""
        errors = _validate_registry_membership(
            live_names={"reg_a", "reg_b"},
            baseline_names={"reg_a", "reg_b"},
        )
        assert errors == []

    def test_live_has_extra_registry(self) -> None:
        """Live registry not in baseline should add error."""
        errors = _validate_registry_membership(
            live_names={"reg_a", "reg_b", "reg_c"},
            baseline_names={"reg_a", "reg_b"},
        )
        assert any("missing live registries" in e for e in errors)
        assert any("reg_c" in e for e in errors)

    def test_baseline_has_stale_registry(self) -> None:
        """Baseline registry not in live should add error."""
        errors = _validate_registry_membership(
            live_names={"reg_a"},
            baseline_names={"reg_a", "reg_stale"},
        )
        assert any("stale" in e for e in errors)
        assert any("reg_stale" in e for e in errors)

    def test_empty_both(self) -> None:
        """Empty sets should produce no errors."""
        errors = _validate_registry_membership(
            live_names=set(),
            baseline_names=set(),
        )
        assert errors == []


class TestValidateRegistryBaselines:
    """Tests for _validate_registry_baselines."""

    def test_within_baseline(self) -> None:
        """Count not exceeding baseline should produce no errors."""
        inventory = _make_inventory(by_registry={"reg_a": 5})
        errors = _validate_registry_baselines(
            baseline_by_registry={"reg_a": 10},
            inventory=inventory,
            comparable_registries=["reg_a"],
        )
        assert errors == []

    def test_exactly_at_baseline(self) -> None:
        """Count equal to baseline should produce no errors."""
        inventory = _make_inventory(by_registry={"reg_a": 10})
        errors = _validate_registry_baselines(
            baseline_by_registry={"reg_a": 10},
            inventory=inventory,
            comparable_registries=["reg_a"],
        )
        assert errors == []

    def test_exceeds_baseline(self) -> None:
        """Count exceeding baseline should add error."""
        inventory = _make_inventory(by_registry={"reg_a": 15})
        errors = _validate_registry_baselines(
            baseline_by_registry={"reg_a": 10},
            inventory=inventory,
            comparable_registries=["reg_a"],
        )
        assert len(errors) == 1
        assert "reg_a" in errors[0]
        assert "15" in errors[0]

    def test_non_int_baseline_value(self) -> None:
        """Non-int baseline value should add error."""
        inventory = _make_inventory(by_registry={"reg_a": 5})
        errors = _validate_registry_baselines(
            baseline_by_registry={"reg_a": "ten"},  # type: ignore[dict-item]
            inventory=inventory,
            comparable_registries=["reg_a"],
        )
        assert any("expected int" in e for e in errors)

    def test_empty_comparable_registries(self) -> None:
        """Empty comparable list should produce no errors."""
        inventory = _make_inventory()
        errors = _validate_registry_baselines(
            baseline_by_registry={},
            inventory=inventory,
            comparable_registries=[],
        )
        assert errors == []


class TestValidateTotalExemptions:
    """Tests for _validate_total_exemptions."""

    def test_within_total_baseline(self) -> None:
        """Total not exceeding baseline should produce no errors."""
        inventory = _make_inventory(total=8)
        errors = _validate_total_exemptions(
            baseline={"total_exemptions": 10},
            inventory=inventory,
        )
        assert errors == []

    def test_exactly_at_total_baseline(self) -> None:
        """Total equal to baseline should produce no errors."""
        inventory = _make_inventory(total=10)
        errors = _validate_total_exemptions(
            baseline={"total_exemptions": 10},
            inventory=inventory,
        )
        assert errors == []

    def test_exceeds_total_baseline(self) -> None:
        """Total exceeding baseline should add error."""
        inventory = _make_inventory(total=15)
        errors = _validate_total_exemptions(
            baseline={"total_exemptions": 10},
            inventory=inventory,
        )
        assert len(errors) == 1
        assert "15" in errors[0]
        assert "10" in errors[0]

    def test_non_int_total_baseline(self) -> None:
        """Non-int total_exemptions in baseline should add error."""
        inventory = _make_inventory(total=5)
        errors = _validate_total_exemptions(
            baseline={"total_exemptions": "ten"},  # type: ignore[dict-item]
            inventory=inventory,
        )
        assert any("expected int" in e for e in errors)

    def test_missing_total_key(self) -> None:
        """Missing total_exemptions key should add error."""
        inventory = _make_inventory(total=5)
        errors = _validate_total_exemptions(
            baseline={},
            inventory=inventory,
        )
        assert any("expected int" in e for e in errors)


class TestValidateRegistrySync:
    """Tests for validate_registry_sync."""

    def test_validate_registry_sync__valid_sync__1adc4e8f(self) -> None:
        """Matching registries within baselines should produce no errors."""
        raw_registry = {
            "registries": {
                "reg_a": {
                    "entry1": {
                        "value": 100,
                        "owner": "alice",
                        "expires_on": "2026-01-01",
                    }
                }
            }
        }
        scorecard = {
            "baseline": {
                "total_exemptions": 1,
                "by_registry": {"reg_a": 1},
            }
        }
        inventory = _make_inventory(
            total=1,
            by_registry={"reg_a": 1},
        )
        errors = validate_registry_sync(
            raw_registry=raw_registry,
            scorecard=scorecard,
            inventory=inventory,
        )
        assert errors == []

    def test_registries_not_dict(self) -> None:
        """Non-dict registries should return error."""
        errors = validate_registry_sync(
            raw_registry={"registries": "invalid"},
            scorecard={},
            inventory=_make_inventory(),
        )
        assert any("expected mapping" in e for e in errors)

    def test_scorecard_baseline_not_dict(self) -> None:
        """Non-dict scorecard baseline should return error."""
        errors = validate_registry_sync(
            raw_registry={"registries": {}},
            scorecard={"baseline": "invalid"},
            inventory=_make_inventory(),
        )
        assert any("expected mapping" in e for e in errors)

    def test_baseline_by_registry_not_dict(self) -> None:
        """Non-dict by_registry should return error."""
        errors = validate_registry_sync(
            raw_registry={"registries": {}},
            scorecard={"baseline": {"by_registry": "invalid"}},
            inventory=_make_inventory(),
        )
        assert any("expected mapping" in e for e in errors)

    def test_missing_live_registry_in_baseline(self) -> None:
        """Registry in live data but not in baseline should add error."""
        raw_registry = {
            "registries": {
                "reg_a": {},
                "reg_b": {},  # not in baseline
            }
        }
        scorecard = {
            "baseline": {
                "total_exemptions": 0,
                "by_registry": {"reg_a": 0},
            }
        }
        inventory = _make_inventory(by_registry={"reg_a": 0, "reg_b": 0})
        errors = validate_registry_sync(
            raw_registry=raw_registry,
            scorecard=scorecard,
            inventory=inventory,
        )
        assert any("missing live registries" in e for e in errors)

    def test_stale_baseline_registry(self) -> None:
        """Registry in baseline but not in live data should add error."""
        raw_registry = {"registries": {"reg_a": {}}}
        scorecard = {
            "baseline": {
                "total_exemptions": 0,
                "by_registry": {"reg_a": 0, "reg_stale": 0},
            }
        }
        inventory = _make_inventory(by_registry={"reg_a": 0})
        errors = validate_registry_sync(
            raw_registry=raw_registry,
            scorecard=scorecard,
            inventory=inventory,
        )
        assert any("stale" in e for e in errors)
