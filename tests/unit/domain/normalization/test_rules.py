"""Tests for normalization rules module."""

from __future__ import annotations

from typing import Any, cast


from bioetl.domain.normalization.rules import (
    normalize_case,
    normalize_cross_pipeline_case,
    normalize_enum_case,
    normalize_null,
    normalize_unit,
)


class TestNormalizeCase:
    """Test case normalization functions."""

    def test_normalize_case_basic(self) -> None:
        """Test basic case normalization."""
        assert normalize_case("test") == "test"
        assert normalize_case("TEST") == "TEST"
        assert normalize_case("Test") == "Test"

    def test_normalize_case_with_allowed_values(self) -> None:
        """Test case normalization with allowed values."""
        allowed = frozenset(["IC50", "EC50", "Ki"])

        # Exact match should return original case
        assert normalize_case("IC50", allowed) == "IC50"
        assert normalize_case("EC50", allowed) == "EC50"
        assert normalize_case("Ki", allowed) == "Ki"

        # Case-insensitive match should return canonical case
        assert normalize_case("ic50", allowed) == "IC50"
        assert normalize_case("ec50", allowed) == "EC50"
        assert normalize_case("ki", allowed) == "Ki"

        # Non-matching values should return None
        assert normalize_case("unknown", allowed) is None
        assert normalize_case("AC50", allowed) is None

    def test_normalize_case_none_and_empty(self) -> None:
        """Test None and empty string handling."""
        assert normalize_case(None) is None
        assert normalize_case("") is None
        assert normalize_case("   ") is None

    def test_normalize_case_non_string(self) -> None:
        """Test non-string input handling."""
        assert normalize_case(123) is None
        assert normalize_case([]) is None
        assert normalize_case({}) is None


class TestNormalizeCrossPipelineCase:
    """Test cross-pipeline case normalization."""

    def test_uppercase_strategy(self) -> None:
        """Test uppercase strategy."""
        assert normalize_cross_pipeline_case("test", "uppercase") == "TEST"
        assert normalize_cross_pipeline_case("Test", "uppercase") == "TEST"
        assert normalize_cross_pipeline_case("TEST", "uppercase") == "TEST"
        assert normalize_cross_pipeline_case("  test  ", "uppercase") == "TEST"

    def test_lowercase_strategy(self) -> None:
        """Test lowercase strategy."""
        assert normalize_cross_pipeline_case("TEST", "lowercase") == "test"
        assert normalize_cross_pipeline_case("Test", "lowercase") == "test"
        assert normalize_cross_pipeline_case("test", "lowercase") == "test"
        assert normalize_cross_pipeline_case("  TEST  ", "lowercase") == "test"

    def test_preserve_strategy(self) -> None:
        """Test preserve strategy."""
        assert normalize_cross_pipeline_case("Test Value", "preserve") == "Test Value"
        assert (
            normalize_cross_pipeline_case("  Test Value  ", "preserve") == "Test Value"
        )
        assert normalize_cross_pipeline_case("In vivo", "preserve") == "In vivo"
        assert normalize_cross_pipeline_case("  In vivo  ", "preserve") == "In vivo"

    def test_invalid_strategy(self) -> None:
        """Test invalid strategy handling."""
        # Should default to preserve behavior for unknown strategies
        assert normalize_cross_pipeline_case("Test", "unknown") == "Test"

    def test_none_and_empty(self) -> None:
        """Test None and empty string handling."""
        none_value = cast(Any, None)
        assert normalize_cross_pipeline_case(none_value, "uppercase") is None
        assert normalize_cross_pipeline_case("", "uppercase") is None
        assert normalize_cross_pipeline_case("   ", "uppercase") is None

    def test_non_string(self) -> None:
        """Test non-string input handling."""
        wrong_int = cast(Any, 123)
        wrong_list = cast(Any, [])
        assert normalize_cross_pipeline_case(wrong_int, "uppercase") is None
        assert normalize_cross_pipeline_case(wrong_list, "uppercase") is None


class TestNormalizeEnumCase:
    """Test enum case normalization."""

    def test_enum_normalization(self) -> None:
        """Test enum value normalization."""
        allowed = frozenset(["IC50", "EC50", "Ki"])

        # Valid values should be normalized
        assert normalize_enum_case("IC50", allowed) == "IC50"
        assert normalize_enum_case("ic50", allowed) == "IC50"
        assert normalize_enum_case("Ki", allowed) == "Ki"
        assert normalize_enum_case("ki", allowed) == "Ki"

        # Invalid values should return None
        assert normalize_enum_case("unknown", allowed) is None
        assert normalize_enum_case("AC50", allowed) is None

    def test_enum_none_and_empty(self) -> None:
        """Test None and empty handling."""
        allowed = frozenset(["IC50", "EC50"])
        assert normalize_enum_case(None, allowed) is None
        assert normalize_enum_case("", allowed) is None
        assert normalize_enum_case("   ", allowed) is None


class TestNormalizeNull:
    """Test null value normalization."""

    def test_null_patterns(self) -> None:
        """Test various null patterns."""
        null_patterns = [
            "N/A",
            "NA",
            "n/a",
            "na",
            "None",
            "NONE",
            "none",
            "Null",
            "NULL",
            "null",
            "-",
            "--",
            ".",
            "..",
            "...",
            "",
            " ",
            "  ",
            "   ",
            "\t",
            "\n",
            "\r",
            "\r\n",
            "<NA>",
            "<na>",
            "<NULL>",
            "<null>",
            "NAN",
            "NaN",
            "nan",
            "NULL_VALUE",
            "MISSING",
            "missing",
            "UNKNOWN",
            "unknown",
            "NOT_AVAILABLE",
            "not_available",
            "NOT_APPLICABLE",
            "not_applicable",
        ]

        for pattern in null_patterns:
            assert normalize_null(pattern) is None

    def test_non_null_values(self) -> None:
        """Test that non-null values are preserved."""
        assert normalize_null("valid") == "valid"
        assert normalize_null("test value") == "test value"
        assert (
            normalize_null("  valid  ") == "  valid  "
        )  # Whitespace preserved for non-null values
        assert normalize_null(123) == 123
        assert normalize_null(["test"]) == ["test"]


class TestNormalizeUnit:
    """Test unit normalization."""

    def test_volume_units(self) -> None:
        """Test volume unit normalization."""
        assert normalize_unit("nL") == "nL"
        assert normalize_unit("NL") == "nL"
        assert normalize_unit("nl") == "nL"
        assert normalize_unit("uL") == "µL"
        assert normalize_unit("UL") == "µL"
        assert normalize_unit("µL") == "µL"
        assert normalize_unit("mL") == "mL"
        assert normalize_unit("ML") == "mL"
        assert normalize_unit("ml") == "mL"
        assert normalize_unit("L") == "L"
        assert normalize_unit("l") == "L"

    def test_concentration_units(self) -> None:
        """Test concentration unit normalization."""
        assert normalize_unit("nM") == "nM"
        assert normalize_unit("NM") == "nM"
        assert normalize_unit("nm") == "nM"
        assert normalize_unit("uM") == "µM"
        assert normalize_unit("UM") == "µM"
        assert normalize_unit("µM") == "µM"
        assert normalize_unit("mM") == "mM"
        assert normalize_unit("MM") == "mM"
        assert normalize_unit("mm") == "mM"
        assert normalize_unit("M") == "M"
        assert normalize_unit("m") == "M"

    def test_other_units(self) -> None:
        """Test other common units."""
        assert normalize_unit("%") == "%"
        assert normalize_unit("percent") == "%"
        assert normalize_unit("PERCENT") == "%"
        assert normalize_unit("U") == "U"
        assert normalize_unit("u") == "U"
        assert normalize_unit("units") == "U"
        assert normalize_unit("UNITS") == "U"

    def test_unknown_units(self) -> None:
        """Test that unknown units are preserved."""
        assert normalize_unit("unknown") == "unknown"
        assert normalize_unit("custom") == "custom"

    def test_none_and_empty(self) -> None:
        """Test None and empty handling."""
        assert normalize_unit(None) is None
        assert normalize_unit("") is None
        assert normalize_unit("   ") is None

    def test_non_string(self) -> None:
        """Test non-string input handling."""
        assert normalize_unit(123) is None
        assert normalize_unit([]) is None
