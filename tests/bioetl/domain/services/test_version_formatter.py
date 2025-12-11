"""Tests for ChEMBL version formatter."""

from bioetl.domain.services.version_formatter import (
    ChemblVersionFormatter,
    format_chembl_version,
)


class TestFormatChemblVersion:
    """Tests for format_chembl_version function."""

    def test_formats_raw_version(self):
        """Raw version number gets chembl_ prefix."""
        assert format_chembl_version("34") == "chembl_34"
        assert format_chembl_version("35") == "chembl_35"

    def test_handles_unknown(self):
        """Unknown version returns 'unknown'."""
        assert format_chembl_version("unknown") == "unknown"

    def test_handles_empty_string(self):
        """Empty string returns 'unknown'."""
        assert format_chembl_version("") == "unknown"

    def test_already_formatted_passes_through(self):
        """Already formatted version is not double-prefixed."""
        assert format_chembl_version("chembl_34") == "chembl_34"

    def test_uppercase_chembl_prefix_normalized(self):
        """ChEMBL_ prefix is normalized to lowercase."""
        assert format_chembl_version("ChEMBL_36") == "chembl_36"
        assert format_chembl_version("CHEMBL_36") == "chembl_36"

    def test_handles_numeric_string(self):
        """Handles version as string of number."""
        assert format_chembl_version("100") == "chembl_100"


class TestChemblVersionFormatter:
    """Tests for ChemblVersionFormatter class."""

    def test_format_method(self):
        """format() method works same as function."""
        formatter = ChemblVersionFormatter()
        assert formatter.format("34") == "chembl_34"
        assert formatter.format("unknown") == "unknown"

    def test_is_valid_with_valid_version(self):
        """is_valid() returns True for valid versions."""
        formatter = ChemblVersionFormatter()
        assert formatter.is_valid("34") is True
        assert formatter.is_valid("chembl_34") is True

    def test_is_valid_with_invalid_version(self):
        """is_valid() returns False for invalid versions."""
        formatter = ChemblVersionFormatter()
        assert formatter.is_valid("unknown") is False
        assert formatter.is_valid("") is False
