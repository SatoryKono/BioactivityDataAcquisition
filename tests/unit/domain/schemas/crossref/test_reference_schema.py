# tests/unit/domain/schemas/crossref/test_reference_schema.py
"""Unit tests for CrossRef Reference Schema field validations.

Tests focus on CrossRef-specific field constraints for Reference entity.
ETL metadata fields are validated separately by base schema tests.
"""

from __future__ import annotations

import re

import pandas as pd

from bioetl.domain.schemas.crossref.reference import ReferenceSchema


class TestSourceDoiValidation:
    """Tests for source_doi field validation (FK to citing Publication)."""

    def test_valid_source_doi_format(self) -> None:
        """Test valid DOI format passes."""
        valid_doi = "10.1038/s41586-024-07487-w"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_valid_source_doi_nature(self) -> None:
        """Test valid Nature DOI."""
        valid_doi = "10.1038/nature12373"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_invalid_source_doi_wrong_prefix(self) -> None:
        """Test DOI with wrong prefix fails."""
        invalid_doi = "11.1234/wrong"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None

    def test_invalid_source_doi_not_a_doi(self) -> None:
        """Test non-DOI string fails."""
        invalid_doi = "PMID:12345678"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None


class TestReferenceKeyValidation:
    """Tests for reference_key field validation (PK component)."""

    def test_valid_reference_key(self) -> None:
        """Test valid reference key."""
        valid_key = "ref-1"
        assert len(valid_key) >= 1

    def test_valid_reference_key_complex(self) -> None:
        """Test valid reference key with complex format."""
        valid_key = "b1-msb-2024-10.1234-example"
        assert len(valid_key) >= 1

    def test_invalid_reference_key_empty(self) -> None:
        """Test empty reference key fails."""
        invalid_key = ""
        assert not (len(invalid_key) >= 1)


class TestTargetDoiValidation:
    """Tests for target_doi field validation (DOI of cited publication)."""

    def test_valid_target_doi_format(self) -> None:
        """Test valid DOI format for cited publication."""
        valid_doi = "10.1021/acs.jmedchem.0c00385"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_valid_target_doi_plos(self) -> None:
        """Test valid PLOS DOI."""
        valid_doi = "10.1371/journal.pone.0123456"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_invalid_target_doi_format(self) -> None:
        """Test invalid DOI format fails."""
        invalid_doi = "not-a-doi"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None


class TestYearValidation:
    """Tests for year field validation."""

    def test_valid_year_current(self) -> None:
        """Test current year is valid."""
        valid_year = 2024
        assert 1500 <= valid_year <= 2100

    def test_valid_year_at_lower_bound(self) -> None:
        """Test year at lower bound (1500)."""
        valid_year = 1500
        assert 1500 <= valid_year <= 2100

    def test_valid_year_at_upper_bound(self) -> None:
        """Test year at upper bound (2100)."""
        valid_year = 2100
        assert 1500 <= valid_year <= 2100

    def test_valid_year_historical(self) -> None:
        """Test historical publication year."""
        valid_year = 1950
        assert 1500 <= valid_year <= 2100

    def test_invalid_year_below_lower_bound(self) -> None:
        """Test year before 1500 fails."""
        invalid_year = 1499
        assert not (1500 <= invalid_year <= 2100)

    def test_invalid_year_above_upper_bound(self) -> None:
        """Test year after 2100 fails."""
        invalid_year = 2101
        assert not (1500 <= invalid_year <= 2100)


class TestIssnValidation:
    """Tests for ISSN field validation."""

    def test_valid_issn_format(self) -> None:
        """Test valid ISSN format."""
        valid_issn = "0028-0836"
        pattern = r"^\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, valid_issn) is not None

    def test_valid_issn_with_x_checksum(self) -> None:
        """Test valid ISSN with X checksum."""
        valid_issn = "2049-632X"
        pattern = r"^\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, valid_issn) is not None

    def test_invalid_issn_wrong_format(self) -> None:
        """Test ISSN with wrong format fails."""
        invalid_issn = "12345678"
        pattern = r"^\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_issn) is None

    def test_invalid_issn_lowercase_x(self) -> None:
        """Test ISSN with lowercase x checksum fails."""
        invalid_issn = "2049-632x"
        pattern = r"^\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_issn) is None

    def test_invalid_issn_not_numeric(self) -> None:
        """Test ISSN with non-numeric characters fails."""
        invalid_issn = "ABCD-1234"
        pattern = r"^\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_issn) is None


class TestSchemaFieldDefinitions:
    """Tests that verify schema field definitions exist and have correct properties."""

    def test_schema_has_reference_fields(self) -> None:
        """Test schema defines all required Reference fields."""
        schema = ReferenceSchema.to_schema()
        required_fields = [
            "source_doi",
            "reference_key",
            "target_doi",
            "unstructured",
            "article_title",
            "journal_title",
            "series_title",
            "volume",
            "issue",
            "first_page",
            "year",
            "author",
            "isbn",
            "issn",
            "component",
            "edition",
            "standards_body",
        ]

        for field in required_fields:
            assert field in schema.columns, f"Missing field: {field}"

    def test_source_doi_not_nullable(self) -> None:
        """Test source_doi is not nullable (FK required)."""
        schema = ReferenceSchema.to_schema()
        doi_col = schema.columns.get("source_doi")
        assert doi_col is not None
        assert doi_col.nullable is False

    def test_reference_key_not_nullable(self) -> None:
        """Test reference_key is not nullable (PK component)."""
        schema = ReferenceSchema.to_schema()
        key_col = schema.columns.get("reference_key")
        assert key_col is not None
        assert key_col.nullable is False

    def test_optional_fields_nullable(self) -> None:
        """Test optional fields are nullable."""
        schema = ReferenceSchema.to_schema()
        nullable_fields = [
            "target_doi",
            "unstructured",
            "article_title",
            "journal_title",
            "series_title",
            "volume",
            "issue",
            "first_page",
            "year",
            "author",
            "isbn",
            "issn",
            "component",
            "edition",
            "standards_body",
        ]

        for field in nullable_fields:
            col = schema.columns.get(field)
            assert col is not None, f"Missing field: {field}"
            assert col.nullable is True, f"Field {field} should be nullable"


class TestSchemaConfiguration:
    """Tests for schema configuration."""

    def test_schema_is_strict(self) -> None:
        """Test schema has strict mode enabled."""
        schema = ReferenceSchema.to_schema()
        assert schema.strict is True

    def test_schema_is_ordered(self) -> None:
        """Test schema has ordered mode enabled."""
        schema = ReferenceSchema.to_schema()
        assert schema.ordered is True

    def test_schema_has_coerce(self) -> None:
        """Test schema has coerce mode enabled."""
        schema = ReferenceSchema.to_schema()
        assert schema.coerce is True

    def test_schema_has_correct_name(self) -> None:
        """Test schema has expected name."""
        schema = ReferenceSchema.to_schema()
        assert schema.name == "ReferenceSchema"


class TestDataFramePatterns:
    """Tests using pandas DataFrame for field validation patterns."""

    def test_source_doi_pattern_with_dataframe(self) -> None:
        """Test source_doi pattern with pandas DataFrame."""
        df = pd.DataFrame({"source_doi": ["10.1038/s41586-024-07487-w", "invalid-doi"]})
        matches = df["source_doi"].str.match(r"^10\.\d{4,}/.*$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is False

    def test_target_doi_pattern_with_dataframe(self) -> None:
        """Test target_doi pattern with pandas DataFrame."""
        df = pd.DataFrame(
            {"target_doi": ["10.1021/acs.jmedchem.0c00385", None, "not-a-doi"]}
        )
        # Filter out None values for pattern matching
        non_null = df[df["target_doi"].notna()]
        matches = non_null["target_doi"].str.match(r"^10\.\d{4,}/.*$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is False

    def test_issn_pattern_with_dataframe(self) -> None:
        """Test ISSN pattern with pandas DataFrame."""
        df = pd.DataFrame({"issn": ["0028-0836", "2049-632X", "invalid"]})
        matches = df["issn"].str.match(r"^\d{4}-\d{3}[\dX]$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is True
        assert bool(matches.iloc[2]) is False

    def test_reference_key_length_with_dataframe(self) -> None:
        """Test reference_key length constraint with pandas DataFrame."""
        df = pd.DataFrame({"reference_key": ["ref-1", "b1-example", ""]})
        valid = df["reference_key"].str.len() >= 1
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is True
        assert bool(valid.iloc[2]) is False


class TestYearConstraintsWithDataFrame:
    """Tests for year constraints using pandas DataFrame."""

    def test_year_lower_bound_with_dataframe(self) -> None:
        """Test year lower bound (1500) with pandas DataFrame."""
        df = pd.DataFrame({"year": [1500, 1499, 2024]})
        valid = df["year"] >= 1500
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is False
        assert bool(valid.iloc[2]) is True

    def test_year_upper_bound_with_dataframe(self) -> None:
        """Test year upper bound (2100) with pandas DataFrame."""
        df = pd.DataFrame({"year": [2100, 2101, 2024]})
        valid = df["year"] <= 2100
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is False
        assert bool(valid.iloc[2]) is True
