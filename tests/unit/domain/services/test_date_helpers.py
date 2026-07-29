# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for date normalization helper functions."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.dates import (
    format_date_parts,
    normalize_partial_date,
)


@pytest.mark.unit
class TestNormalizePartialDate:
    """Tests for normalize_partial_date()."""

    def test_none_input_returns_none(self) -> None:
        """Test that None input returns None."""
        assert normalize_partial_date(None) is None

    def test_normalize_partial_date__string_returns_none__fdcfa2d7(self) -> None:
        """Test that empty string returns None."""
        assert normalize_partial_date("") is None

    def test_whitespace_only_returns_none(self) -> None:
        """Test that whitespace-only string returns None."""
        assert normalize_partial_date("   ") is None

    def test_normalize_partial_date__full_date_unchanged__62e6b2a5(self) -> None:
        """Test that full YYYY-MM-DD date is returned unchanged."""
        assert normalize_partial_date("2024-03-15") == "2024-03-15"

    def test_full_date_invalid_format_returns_none(self) -> None:
        """Test that full-length but invalid format returns None."""
        # Length 10 but not YYYY-MM-DD format
        assert normalize_partial_date("2024/03/15") is None

    def test_partial_month_normalized_to_end_of_month(self) -> None:
        """Test that YYYY-MM is normalized to the last day of month."""
        assert normalize_partial_date("2024-03") == "2024-03-31"

    def test_partial_month_january(self) -> None:
        """Test that YYYY-MM for January is normalized to YYYY-01-31."""
        assert normalize_partial_date("2024-01") == "2024-01-31"

    def test_partial_month_february_respects_month_length(self) -> None:
        """Test leap and non-leap February partial dates."""
        assert normalize_partial_date("2024-02") == "2024-02-29"
        assert normalize_partial_date("2023-02") == "2023-02-28"

    def test_partial_month_invalid_format_returns_none(self) -> None:
        """Test that 7-char string without dash at position 4 returns None."""
        assert normalize_partial_date("2024/03") is None

    def test_partial_year_normalized_to_end_of_year(self) -> None:
        """Test that YYYY is normalized to YYYY-12-31."""
        assert normalize_partial_date("2024") == "2024-12-31"

    def test_partial_year_not_digits_returns_none(self) -> None:
        """Test that 4-char non-digit string returns None."""
        assert normalize_partial_date("abcd") is None

    def test_unknown_length_returns_none(self) -> None:
        """Test that string with unknown length returns None."""
        assert normalize_partial_date("2024-3") is None  # Length 6, no handler
        assert normalize_partial_date("20241201") is None  # Length 8, no handler

    def test_whitespace_is_stripped(self) -> None:
        """Test that leading/trailing whitespace is stripped before processing."""
        assert normalize_partial_date("  2024  ") == "2024-12-31"
        assert normalize_partial_date("  2024-03  ") == "2024-03-31"
        assert normalize_partial_date("  2024-03-15  ") == "2024-03-15"

    @pytest.mark.parametrize(
        "date_str, expected",
        [
            ("2024-03-15", "2024-03-15"),
            ("2024-03", "2024-03-31"),
            ("2024", "2024-12-31"),
            (None, None),
            ("", None),
        ],
    )
    def test_parametrized_cases(
        self, date_str: str | None, expected: str | None
    ) -> None:
        """Test various date normalization cases."""
        assert normalize_partial_date(date_str) == expected


@pytest.mark.unit
class TestFormatDateParts:
    """Tests for format_date_parts()."""

    def test_format_date_parts__input_returns_none__6eee72a5(self) -> None:
        """Test that None input returns None."""
        assert format_date_parts(None) is None

    def test_format_date_parts__list_returns_none__007dd84e(self) -> None:
        """Test that empty list returns None."""
        assert format_date_parts([]) is None

    def test_empty_inner_list_returns_none(self) -> None:
        """Test that list with empty inner list returns None."""
        assert format_date_parts([[]]) is None

    def test_full_date_parts(self) -> None:
        """Test complete year-month-day date parts."""
        result = format_date_parts([[2024, 3, 15]])
        assert result == "2024-03-15"

    def test_month_only_date_parts(self) -> None:
        """Test year-month date parts returns last day of month."""
        result = format_date_parts([[2024, 3]])
        assert result == "2024-03-31"

    def test_year_only_date_parts(self) -> None:
        """Test year-only date parts returns last day of year."""
        result = format_date_parts([[2024]])
        assert result == "2024-12-31"

    def test_february_leap_year(self) -> None:
        """Test February date parts in leap year returns correct last day."""
        result = format_date_parts([[2024, 2]])
        assert result == "2024-02-29"

    def test_february_non_leap_year(self) -> None:
        """Test February date parts in non-leap year returns correct last day."""
        result = format_date_parts([[2023, 2]])
        assert result == "2023-02-28"

    def test_december_returns_31(self) -> None:
        """Test December returns day 31."""
        result = format_date_parts([[2024, 12]])
        assert result == "2024-12-31"

    def test_zero_padding(self) -> None:
        """Test that month and day values are zero-padded."""
        result = format_date_parts([[2024, 1, 5]])
        assert result == "2024-01-05"

    def test_only_first_inner_list_used(self) -> None:
        """Test that only the first inner list is used (CrossRef format)."""
        result = format_date_parts([[2024, 3, 15], [2020, 1, 1]])
        assert result == "2024-03-15"

    @pytest.mark.parametrize(
        "date_parts, expected",
        [
            ([[2024, 3, 15]], "2024-03-15"),
            ([[2024, 3]], "2024-03-31"),
            ([[2024]], "2024-12-31"),
            ([[2020, 2]], "2020-02-29"),  # leap year
            (None, None),
            ([], None),
        ],
    )
    def test_format_date_parts__parametrized_cases__86c75be0(
        self,
        date_parts: list[list[int]] | None,
        expected: str | None,
    ) -> None:
        """Test various date parts formatting cases."""
        assert format_date_parts(date_parts) == expected
