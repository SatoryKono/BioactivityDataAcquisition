"""Unit tests for inventory module."""

from __future__ import annotations

from collections import Counter
from datetime import date
from unittest.mock import patch

import pytest

from bioetl.infrastructure.quality.inventory import (
    ExemptionInventorySummary,
    _resolve_owner,
    _tally_expiry,
    build_exemption_inventory,
)


pytestmark = pytest.mark.unit

class TestExemptionInventorySummary:
    """Tests for ExemptionInventorySummary dataclass."""

    def test_inventory_summary__creation__852533c7(self) -> None:
        """Should be creatable with expected fields."""
        summary = ExemptionInventorySummary(
            total_exemptions=10,
            by_registry={"reg_a": 10},
            by_owner={"alice": 10},
            by_expiry_quarter={"2025-Q4": 10},
            expired_entries=2,
        )
        assert summary.total_exemptions == 10
        assert summary.by_registry == {"reg_a": 10}
        assert summary.expired_entries == 2

    def test_inventory_summary__frozen__a99f0110(self) -> None:
        """Should be immutable (frozen dataclass)."""
        summary = ExemptionInventorySummary(
            total_exemptions=0,
            by_registry={},
            by_owner={},
            by_expiry_quarter={},
            expired_entries=0,
        )
        with pytest.raises(Exception):
            summary.total_exemptions = 5  # type: ignore[misc]


class TestResolveOwner:
    """Tests for _resolve_owner."""

    def test_valid_owner_string(self) -> None:
        """Valid owner string should be returned stripped."""
        assert _resolve_owner({"owner": "  alice  "}) == "alice"

    def test_missing_owner(self) -> None:
        """Missing owner key should return '<missing>'."""
        assert _resolve_owner({}) == "<missing>"

    def test_none_owner(self) -> None:
        """None owner should return '<missing>'."""
        assert _resolve_owner({"owner": None}) == "<missing>"

    def test_empty_owner(self) -> None:
        """Empty string owner should return '<missing>'."""
        assert _resolve_owner({"owner": "   "}) == "<missing>"

    def test_non_string_owner(self) -> None:
        """Non-string owner should return '<missing>'."""
        assert _resolve_owner({"owner": 42}) == "<missing>"


class TestTallyExpiry:
    """Tests for _tally_expiry."""

    def test_future_date_not_expired(self) -> None:
        """Entry with future expiry should not be expired."""
        by_expiry: Counter[str] = Counter()
        result = _tally_expiry(
            {"expires_on": "2026-12-31"},
            date(2025, 6, 15),
            by_expiry,
        )
        assert result == 0
        assert "2026-Q4" in by_expiry

    def test_past_date_expired(self) -> None:
        """Entry with past expiry should be counted as expired."""
        by_expiry: Counter[str] = Counter()
        result = _tally_expiry(
            {"expires_on": "2024-01-01"},
            date(2025, 6, 15),
            by_expiry,
        )
        assert result == 1
        assert "2024-Q1" in by_expiry

    def test_missing_expires_on(self) -> None:
        """Missing expires_on should count in 'unknown' quarter."""
        by_expiry: Counter[str] = Counter()
        result = _tally_expiry({}, date(2025, 6, 15), by_expiry)
        assert result == 0
        assert by_expiry["unknown"] == 1

    def test_invalid_date_string(self) -> None:
        """Invalid date string should count in 'unknown' quarter."""
        by_expiry: Counter[str] = Counter()
        result = _tally_expiry(
            {"expires_on": "not-a-date"},
            date(2025, 6, 15),
            by_expiry,
        )
        assert result == 0
        assert by_expiry["unknown"] == 1


class TestBuildExemptionInventory:
    """Tests for build_exemption_inventory."""

    def _mock_registry(self) -> dict[str, object]:
        return {
            "registries": {
                "reg_a": {
                    "entry1": {
                        "value": 500,
                        "owner": "alice",
                        "reason": "legacy",
                        "expires_on": "2026-01-01",
                        "removal_step": "refactor",
                    },
                    "entry2": {
                        "value": 600,
                        "owner": "bob",
                        "reason": "old code",
                        "expires_on": "2024-01-01",  # expired
                        "removal_step": "rewrite",
                    },
                },
                "reg_b": {
                    "entry3": {
                        "value": 200,
                        "owner": "carol",
                        "expires_on": "2026-06-01",
                        "removal_step": "cleanup",
                    },
                },
            }
        }

    def test_builds_correct_totals(self) -> None:
        """Should count all entries across registries."""
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=self._mock_registry(),
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert summary.total_exemptions == 3
        assert summary.by_registry == {"reg_a": 2, "reg_b": 1}

    def test_counts_by_owner(self) -> None:
        """Should count exemptions by owner."""
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=self._mock_registry(),
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert summary.by_owner["alice"] == 1
        assert summary.by_owner["bob"] == 1
        assert summary.by_owner["carol"] == 1

    def test_counts_expired_entries(self) -> None:
        """Should count entries with past expiry dates."""
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=self._mock_registry(),
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert summary.expired_entries == 1  # entry2 is expired

    def test_by_expiry_quarter_populated(self) -> None:
        """Should count entries by expiry quarter."""
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=self._mock_registry(),
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert sum(summary.by_expiry_quarter.values()) == 3

    def test_skips_non_dict_registry(self) -> None:
        """Non-dict registry entries should be skipped."""
        raw = {
            "registries": {
                "reg_a": "not_a_dict",
                "reg_b": {
                    "entry": {
                        "value": 100,
                        "owner": "alice",
                        "expires_on": "2026-01-01",
                    }
                },
            }
        }
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=raw,
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert summary.total_exemptions == 1
        assert "reg_a" not in summary.by_registry

    def test_exemption_inventory__non_dict_entries__b9f4e8d8(self) -> None:
        """Non-dict exemption entries should be skipped."""
        raw = {
            "registries": {
                "reg_a": {
                    "entry1": "not_a_dict",
                    "entry2": {"owner": "alice", "expires_on": "2026-01-01"},
                }
            }
        }
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=raw,
        ):
            summary = build_exemption_inventory(today=date(2025, 6, 15))

        assert summary.total_exemptions == 1

    def test_raises_for_invalid_registries_structure(self) -> None:
        """Non-dict 'registries' should raise ValueError."""
        raw = {"registries": "not_a_dict"}
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=raw,
        ):
            with pytest.raises(ValueError, match="must be a mapping"):
                build_exemption_inventory(today=date(2025, 6, 15))

    def test_exemption_inventory__to_date_today__afda8355(self) -> None:
        """today=None should use date.today() without error."""
        raw: dict[str, object] = {"registries": {}}
        with patch(
            "bioetl.infrastructure.quality.inventory.load_exemptions_registry",
            return_value=raw,
        ):
            summary = build_exemption_inventory()

        assert summary.total_exemptions == 0
