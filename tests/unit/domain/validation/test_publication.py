"""Tests for publication validation functions.

Tests for validate_doi, validate_publication_year, validate_year_range.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.validation import ValidationConfig
from bioetl.domain.validation.publication import (
    DOI_REGEX_PATTERN,
    MAX_PUBLICATION_YEAR,
    MIN_PUBLICATION_YEAR,
    validate_doi,
    validate_publication_year,
    validate_year_range,
)


@pytest.mark.unit
class TestValidateDoi:
    """Tests for validate_doi function."""

    def test_valid_nature_doi(self) -> None:
        assert validate_doi("10.1038/nature12373") is True

    def test_valid_simple_doi(self) -> None:
        assert validate_doi("10.1000/xyz123") is True

    def test_valid_plos_doi(self) -> None:
        assert validate_doi("10.1371/journal.pone.0012345") is True

    def test_invalid_format(self) -> None:
        assert validate_doi("invalid") is False

    def test_none_returns_false(self) -> None:
        assert validate_doi(None) is False

    def test_empty_string_returns_false(self) -> None:
        assert validate_doi("") is False

    def test_missing_prefix(self) -> None:
        assert validate_doi("1038/nature12373") is False

    def test_strips_whitespace(self) -> None:
        assert validate_doi("  10.1038/nature12373  ") is True

    def test_doi_regex_pattern_exported(self) -> None:
        assert DOI_REGEX_PATTERN == r"^10\.\d{4,}/\S+$"


@pytest.mark.unit
class TestValidatePublicationYear:
    """Tests for validate_publication_year function."""

    def test_valid_year(self) -> None:
        year, is_warning = validate_publication_year(2020)
        assert year == 2020
        assert is_warning is False

    def test_none_returns_none_no_warning(self) -> None:
        year, is_warning = validate_publication_year(None)
        assert year is None
        assert is_warning is False

    def test_year_below_min_flags_warning(self) -> None:
        year, is_warning = validate_publication_year(1499)
        assert year == 1499
        assert is_warning is True

    def test_year_above_max_flags_warning(self) -> None:
        year, is_warning = validate_publication_year(2101)
        assert year == 2101
        assert is_warning is True

    def test_boundary_min_no_warning(self) -> None:
        year, is_warning = validate_publication_year(1500)
        assert year == 1500
        assert is_warning is False

    def test_boundary_max_no_warning(self) -> None:
        year, is_warning = validate_publication_year(2100)
        assert year == 2100
        assert is_warning is False

    def test_custom_config(self) -> None:
        config = ValidationConfig(min_publication_year=2000, max_publication_year=2025)
        year, is_warning = validate_publication_year(1999, config=config)
        assert year == 1999
        assert is_warning is True


@pytest.mark.unit
class TestValidateYearRange:
    """Tests for validate_year_range function."""

    def test_valid_year(self) -> None:
        assert validate_year_range(2024) is True

    def test_below_min(self) -> None:
        assert validate_year_range(1949) is False

    def test_above_max(self) -> None:
        assert validate_year_range(2051) is False

    def test_none_returns_false(self) -> None:
        assert validate_year_range(None) is False

    def test_min_boundary(self) -> None:
        assert validate_year_range(MIN_PUBLICATION_YEAR) is True

    def test_max_boundary(self) -> None:
        assert validate_year_range(MAX_PUBLICATION_YEAR) is True

    def test_custom_range__test_validate_year_range_domain_validation_test_publication_116(
        self,
    ) -> None:
        assert validate_year_range(2000, min_year=1990, max_year=2010) is True
        assert validate_year_range(1989, min_year=1990, max_year=2010) is False
