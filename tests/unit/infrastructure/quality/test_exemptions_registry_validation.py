"""Unit tests for exemptions_registry_validation module."""

from __future__ import annotations

from datetime import date

from bioetl.infrastructure.quality.exemptions_registry_validation import (
    _normalize_required_fields,
    _resolve_due_field,
    _validate_due_date,
    _validate_owner,
    _validate_required_fields,
    get_policy_required_fields,
    validate_exemption_entry,
)


class TestValidateRequiredFields:
    """Tests for _validate_required_fields."""

    def test_all_fields_present(self) -> None:
        """All required fields present should produce no errors."""
        errors: list[str] = []
        _validate_required_fields(
            "prefix",
            {"owner": "alice", "reason": "justification", "removal_step": "step"},
            ("owner", "reason", "removal_step"),
            errors,
        )
        assert errors == []

    def test_missing_field(self) -> None:
        """Missing required field should add error."""
        errors: list[str] = []
        _validate_required_fields(
            "prefix",
            {"owner": "alice"},
            ("owner", "reason", "removal_step"),
            errors,
        )
        assert any("reason" in e for e in errors)
        assert any("removal_step" in e for e in errors)

    def test_empty_string_value(self) -> None:
        """Empty string for required field should add error."""
        errors: list[str] = []
        _validate_required_fields(
            "prefix",
            {"owner": "  "},  # whitespace only
            ("owner",),
            errors,
        )
        assert any("owner" in e for e in errors)

    def test_due_date_fields_skipped(self) -> None:
        """Due-date fields like 'expires_on' should be skipped (handled separately)."""
        errors: list[str] = []
        _validate_required_fields(
            "prefix",
            {},  # empty entry – no expires_on
            ("expires_on",),
            errors,
        )
        # No error because expires_on is a due-date field, handled by _validate_due_date
        assert errors == []

    def test_none_value(self) -> None:
        """None value for required field should add error."""
        errors: list[str] = []
        _validate_required_fields(
            "prefix",
            {"owner": None},
            ("owner",),
            errors,
        )
        assert any("owner" in e for e in errors)


class TestNormalizeRequiredFields:
    """Tests for _normalize_required_fields."""

    def test_valid_list(self) -> None:
        """Valid list of field names should return tuple."""
        errors: list[str] = []
        result = _normalize_required_fields(
            ["owner", "reason", "expires_on", "removal_step"],
            errors,
        )
        assert result == ("owner", "reason", "expires_on", "removal_step")
        assert errors == []

    def test_not_a_list(self) -> None:
        """Non-list should add error and return defaults."""
        errors: list[str] = []
        result = _normalize_required_fields("not_a_list", errors)
        assert len(errors) == 1
        assert "required_fields" in errors[0]
        # Should fall back to defaults
        assert "owner" in result

    def test_empty_list_returns_defaults(self) -> None:
        """Empty list should add error and return defaults."""
        errors: list[str] = []
        result = _normalize_required_fields([], errors)
        assert len(errors) >= 1
        assert "owner" in result

    def test_invalid_items_skipped(self) -> None:
        """Non-string or empty items should add error and be skipped."""
        errors: list[str] = []
        result = _normalize_required_fields(
            ["owner", "", 42, "reason"],
            errors,
        )
        assert "owner" in result
        assert "reason" in result
        assert len(errors) >= 2  # empty string and int

    def test_whitespace_stripped(self) -> None:
        """Items with whitespace should be stripped."""
        errors: list[str] = []
        result = _normalize_required_fields(["  owner  ", " reason "], errors)
        assert "owner" in result
        assert "reason" in result


class TestGetPolicyRequiredFields:
    """Tests for get_policy_required_fields."""

    def test_valid_policy(self) -> None:
        """Valid policy with all required fields should return without errors."""
        raw = {
            "policy": {
                "required_fields": [
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            }
        }
        errors: list[str] = []
        result = get_policy_required_fields(raw, errors)
        assert "owner" in result
        assert "classification" in result
        assert "linked_rf" in result
        assert "removal_step" in result
        assert errors == []

    def test_policy_not_dict(self) -> None:
        """Non-dict policy should add error and use defaults."""
        raw = {"policy": "invalid"}
        errors: list[str] = []
        result = get_policy_required_fields(raw, errors)
        assert any("policy" in e for e in errors)
        assert "owner" in result

    def test_missing_owner_in_fields(self) -> None:
        """Policy without 'owner' should add error."""
        raw = {
            "policy": {
                "required_fields": [
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            }
        }
        errors: list[str] = []
        get_policy_required_fields(raw, errors)
        assert any("owner" in e for e in errors)

    def test_missing_classification(self) -> None:
        """Policy without 'classification' should add error."""
        raw = {
            "policy": {
                "required_fields": [
                    "owner",
                    "reason",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            }
        }
        errors: list[str] = []
        get_policy_required_fields(raw, errors)
        assert any("classification" in e for e in errors)

    def test_missing_linked_rf(self) -> None:
        """Policy without 'linked_rf' should add error."""
        raw = {
            "policy": {
                "required_fields": [
                    "owner",
                    "reason",
                    "classification",
                    "expires_on",
                    "removal_step",
                ]
            }
        }
        errors: list[str] = []
        get_policy_required_fields(raw, errors)
        assert any("linked_rf" in e for e in errors)

    def test_missing_removal_step(self) -> None:
        """Policy without 'removal_step' should add error."""
        raw = {
            "policy": {
                "required_fields": [
                    "owner",
                    "classification",
                    "linked_rf",
                    "expires_on",
                ]
            }
        }
        errors: list[str] = []
        get_policy_required_fields(raw, errors)
        assert any("removal_step" in e for e in errors)

    def test_missing_due_date_field(self) -> None:
        """Policy without any due-date field should add error."""
        raw = {
            "policy": {
                "required_fields": [
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "removal_step",
                ]
            }
        }
        errors: list[str] = []
        get_policy_required_fields(raw, errors)
        assert any("due date" in e for e in errors)


class TestValidateOwner:
    """Tests for _validate_owner."""

    def test_valid_owner(self) -> None:
        """Real owner name should produce no errors."""
        errors: list[str] = []
        _validate_owner("prefix", {"owner": "alice"}, errors)
        assert errors == []

    def test_placeholder_todo(self) -> None:
        """Placeholder 'todo' owner should add error."""
        errors: list[str] = []
        _validate_owner("prefix", {"owner": "todo"}, errors)
        assert any("placeholder" in e for e in errors)

    def test_placeholder_tbd(self) -> None:
        """Placeholder 'tbd' owner should add error."""
        errors: list[str] = []
        _validate_owner("prefix", {"owner": "tbd"}, errors)
        assert any("placeholder" in e for e in errors)

    def test_placeholder_unknown(self) -> None:
        """Placeholder 'unknown' owner should add error."""
        errors: list[str] = []
        _validate_owner("prefix", {"owner": "Unknown"}, errors)
        assert any("placeholder" in e for e in errors)

    def test_missing_owner_no_error(self) -> None:
        """Missing owner key should not add error (handled by required fields)."""
        errors: list[str] = []
        _validate_owner("prefix", {}, errors)
        assert errors == []

    def test_non_string_owner_no_error(self) -> None:
        """Non-string owner should not trigger placeholder check."""
        errors: list[str] = []
        _validate_owner("prefix", {"owner": 42}, errors)
        assert errors == []


class TestResolveDueField:
    """Tests for _resolve_due_field."""

    def test_expires_on_in_required_and_entry(self) -> None:
        """expires_on in required_fields and entry should be selected."""
        result = _resolve_due_field(
            {"expires_on": "2025-12-31"},
            ("owner", "expires_on", "removal_step"),
        )
        assert result == "expires_on"

    def test_due_on_in_entry(self) -> None:
        """due_on in entry should be selected when expires_on not present."""
        result = _resolve_due_field(
            {"due_on": "2025-12-31"},
            ("owner", "due_on"),
        )
        assert result == "due_on"

    def test_fallback_to_first_candidate(self) -> None:
        """When no due-date field in entry, return first candidate."""
        result = _resolve_due_field(
            {},
            ("owner", "expires_on"),
        )
        assert result == "expires_on"


class TestValidateDueDate:
    """Tests for _validate_due_date."""

    def test_valid_future_date(self) -> None:
        """Valid future date should produce no errors."""
        errors: list[str] = []
        expired: list[str] = []
        _validate_due_date(
            "prefix",
            {"expires_on": "2026-12-31"},
            ("expires_on",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert errors == []
        assert expired == []

    def test_expired_date(self) -> None:
        """Past date should add to expired_entries."""
        errors: list[str] = []
        expired: list[str] = []
        _validate_due_date(
            "prefix",
            {"expires_on": "2024-01-01"},
            ("expires_on",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert errors == []
        assert len(expired) == 1

    def test_not_string_due_date(self) -> None:
        """Non-string due date should add error."""
        errors: list[str] = []
        expired: list[str] = []
        _validate_due_date(
            "prefix",
            {"expires_on": 20251231},
            ("expires_on",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("must be ISO date string" in e for e in errors)

    def test_invalid_date_format(self) -> None:
        """Invalid date format should add error."""
        errors: list[str] = []
        expired: list[str] = []
        _validate_due_date(
            "prefix",
            {"expires_on": "not-a-date"},
            ("expires_on",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("YYYY-MM-DD" in e for e in errors)


class TestValidateExemptionEntry:
    """Tests for validate_exemption_entry."""

    def _valid_entry(self) -> dict[str, object]:
        return {
            "value": 500,
            "owner": "alice",
            "reason": "legacy code",
            "classification": "technical_debt",
            "linked_rf": "RF-001",
            "expires_on": "2026-12-31",
            "removal_step": "refactor module",
        }

    def test_valid_entry(self) -> None:
        """Valid entry should produce no errors."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            "my_module.py",
            self._valid_entry(),
            (
                "value",
                "owner",
                "reason",
                "classification",
                "linked_rf",
                "expires_on",
                "removal_step",
            ),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert errors == []
        assert expired == []

    def test_empty_name(self) -> None:
        """Empty exemption name should add error."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            "   ",
            self._valid_entry(),
            ("owner",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("non-empty string" in e for e in errors)

    def test_non_string_name(self) -> None:
        """Non-string exemption name should add error."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            42,
            self._valid_entry(),
            ("owner",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("non-empty string" in e for e in errors)

    def test_placeholder_name(self) -> None:
        """Placeholder name should add error."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            "todo",
            self._valid_entry(),
            ("owner",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("placeholder" in e for e in errors)

    def test_entry_not_dict(self) -> None:
        """Non-dict entry should add error."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            "valid_name",
            "not_a_dict",
            ("owner",),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("entry must be mapping" in e for e in errors)

    def test_expired_entry_tracked(self) -> None:
        """Entry with past expiry date should be tracked in expired_entries."""
        errors: list[str] = []
        expired: list[str] = []
        validate_exemption_entry(
            "reg_a",
            "old_module.py",
            {
                "value": 100,
                "owner": "alice",
                "reason": "old",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2020-01-01",
                "removal_step": "fix it",
            },
            (
                "value",
                "owner",
                "reason",
                "classification",
                "linked_rf",
                "expires_on",
                "removal_step",
            ),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert len(expired) == 1

    def test_invalid_classification_adds_error(self) -> None:
        """Unknown classification should be rejected."""
        errors: list[str] = []
        expired: list[str] = []
        entry = self._valid_entry()
        entry["classification"] = "temporary"
        validate_exemption_entry(
            "reg_a",
            "my_module.py",
            entry,
            (
                "value",
                "owner",
                "reason",
                "classification",
                "linked_rf",
                "expires_on",
                "removal_step",
            ),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("classification must be one of" in error for error in errors)

    def test_invalid_linked_rf_adds_error(self) -> None:
        """Tracking id should follow RF-001/QG-001 style format."""
        errors: list[str] = []
        expired: list[str] = []
        entry = self._valid_entry()
        entry["linked_rf"] = "ticket-1"
        validate_exemption_entry(
            "reg_a",
            "my_module.py",
            entry,
            (
                "value",
                "owner",
                "reason",
                "classification",
                "linked_rf",
                "expires_on",
                "removal_step",
            ),
            date(2025, 6, 15),
            errors,
            expired,
        )
        assert any("linked_rf must match" in error for error in errors)
