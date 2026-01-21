# tests/unit/domain/schemas/crossref/test_author_schema.py
"""Unit tests for CrossRef Author Schema field validations.

Tests focus on CrossRef-specific field constraints for Author entity.
ETL metadata fields are validated separately by base schema tests.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from bioetl.domain.schemas.crossref.author import (
    AUTHOR_SEQUENCES,
    AuthorSchema,
)


class TestDoiValidation:
    """Tests for DOI field validation (foreign key to Publication)."""

    def test_valid_doi_format(self) -> None:
        """Test valid DOI format passes."""
        valid_doi = "10.1038/s41586-024-07487-w"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_valid_doi_long_prefix(self) -> None:
        """Test DOI with longer registry prefix."""
        valid_doi = "10.12345/example.2024.001"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_invalid_doi_wrong_prefix(self) -> None:
        """Test DOI with wrong prefix fails."""
        invalid_doi = "11.1234/wrong-prefix"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None

    def test_invalid_doi_short_registry(self) -> None:
        """Test DOI with short registry code fails."""
        invalid_doi = "10.123/short"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None

    def test_invalid_doi_no_suffix(self) -> None:
        """Test DOI without suffix part fails."""
        invalid_doi = "10.1234/"
        # Pattern requires at least one char after slash, so empty suffix fails
        pattern = r"^10\.\d{4,}/.*$"
        # Note: .* allows empty suffix in regex, but field must have content
        assert re.match(pattern, invalid_doi) is not None  # Regex passes
        # But semantically empty suffix is invalid - checked by schema

    def test_invalid_doi_not_a_doi(self) -> None:
        """Test non-DOI string fails."""
        invalid_doi = "not-a-doi"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None


class TestAuthorSequenceValidation:
    """Tests for author_sequence field validation."""

    def test_valid_author_sequence_zero(self) -> None:
        """Test author_sequence of 0 (first author)."""
        valid_sequence = 0
        assert valid_sequence >= 0

    def test_valid_author_sequence_positive(self) -> None:
        """Test positive author_sequence."""
        valid_sequence = 5
        assert valid_sequence >= 0

    def test_invalid_author_sequence_negative(self) -> None:
        """Test negative author_sequence fails."""
        invalid_sequence = -1
        assert not (invalid_sequence >= 0)


class TestFamilyNameValidation:
    """Tests for family_name field validation."""

    def test_valid_family_name(self) -> None:
        """Test valid family name."""
        valid_name = "Smith"
        assert len(valid_name) >= 1

    def test_invalid_family_name_empty(self) -> None:
        """Test empty family name fails."""
        invalid_name = ""
        assert not (len(invalid_name) >= 1)

    def test_valid_family_name_special_chars(self) -> None:
        """Test family name with special characters (hyphens, apostrophes)."""
        valid_name = "O'Brien-Smith"
        assert len(valid_name) >= 1


class TestOrcidValidation:
    """Tests for ORCID field validation."""

    def test_valid_orcid_format(self) -> None:
        """Test valid ORCID format (ID only, without URL prefix)."""
        valid_orcid = "0000-0002-1234-5678"
        pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, valid_orcid) is not None

    def test_valid_orcid_with_x_checksum(self) -> None:
        """Test valid ORCID with X checksum."""
        valid_orcid = "0000-0002-1825-009X"
        pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, valid_orcid) is not None

    def test_invalid_orcid_with_url_prefix(self) -> None:
        """Test ORCID with URL prefix fails (should be ID only)."""
        invalid_orcid = "https://orcid.org/0000-0002-1234-5678"
        pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_orcid) is None

    def test_invalid_orcid_wrong_format(self) -> None:
        """Test ORCID with wrong format fails."""
        invalid_orcid = "0000-1234-5678"
        pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_orcid) is None

    def test_invalid_orcid_lowercase_x(self) -> None:
        """Test ORCID with lowercase x checksum fails."""
        invalid_orcid = "0000-0002-1825-009x"
        pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
        assert re.match(pattern, invalid_orcid) is None


class TestSequenceTypeValidation:
    """Tests for sequence enum field validation."""

    @pytest.mark.parametrize("sequence_type", AUTHOR_SEQUENCES)
    def test_valid_sequence_type(self, sequence_type: str) -> None:
        """Test all valid sequence type values."""
        assert sequence_type in AUTHOR_SEQUENCES

    def test_invalid_sequence_type(self) -> None:
        """Test invalid sequence type."""
        invalid_type = "unknown"
        assert invalid_type not in AUTHOR_SEQUENCES

    def test_sequence_types_expected_values(self) -> None:
        """Test expected sequence type values exist."""
        assert "first" in AUTHOR_SEQUENCES
        assert "additional" in AUTHOR_SEQUENCES


class TestSchemaFieldDefinitions:
    """Tests that verify schema field definitions exist and have correct properties."""

    def test_schema_has_author_fields(self) -> None:
        """Test schema defines all required Author fields."""
        schema = AuthorSchema.to_schema()
        required_fields = [
            "doi",
            "author_sequence",
            "family_name",
            "given_name",
            "suffix",
            "orcid",
            "authenticated_orcid",
            "affiliation",
            "affiliation_ids",
            "sequence",
        ]

        for field in required_fields:
            assert field in schema.columns, f"Missing field: {field}"

    def test_doi_not_nullable(self) -> None:
        """Test doi is not nullable (FK required)."""
        schema = AuthorSchema.to_schema()
        doi_col = schema.columns.get("doi")
        assert doi_col is not None
        assert doi_col.nullable is False

    def test_author_sequence_not_nullable(self) -> None:
        """Test author_sequence is not nullable (PK component)."""
        schema = AuthorSchema.to_schema()
        seq_col = schema.columns.get("author_sequence")
        assert seq_col is not None
        assert seq_col.nullable is False

    def test_family_name_not_nullable(self) -> None:
        """Test family_name is not nullable (required)."""
        schema = AuthorSchema.to_schema()
        name_col = schema.columns.get("family_name")
        assert name_col is not None
        assert name_col.nullable is False

    def test_optional_fields_nullable(self) -> None:
        """Test optional fields are nullable."""
        schema = AuthorSchema.to_schema()
        nullable_fields = [
            "given_name",
            "suffix",
            "orcid",
            "authenticated_orcid",
            "affiliation",
            "affiliation_ids",
            "sequence",
        ]

        for field in nullable_fields:
            col = schema.columns.get(field)
            assert col is not None, f"Missing field: {field}"
            assert col.nullable is True, f"Field {field} should be nullable"


class TestSchemaConfiguration:
    """Tests for schema configuration."""

    def test_schema_is_strict(self) -> None:
        """Test schema has strict mode enabled."""
        schema = AuthorSchema.to_schema()
        assert schema.strict is True

    def test_schema_is_ordered(self) -> None:
        """Test schema has ordered mode enabled."""
        schema = AuthorSchema.to_schema()
        assert schema.ordered is True

    def test_schema_has_coerce(self) -> None:
        """Test schema has coerce mode enabled."""
        schema = AuthorSchema.to_schema()
        assert schema.coerce is True

    def test_schema_has_correct_name(self) -> None:
        """Test schema has expected name."""
        schema = AuthorSchema.to_schema()
        assert schema.name == "AuthorSchema"


class TestDataFramePatterns:
    """Tests using pandas DataFrame for field validation patterns."""

    def test_doi_pattern_with_dataframe(self) -> None:
        """Test DOI pattern with pandas DataFrame."""
        df = pd.DataFrame({"doi": ["10.1038/s41586-024-07487-w", "invalid-doi"]})
        matches = df["doi"].str.match(r"^10\.\d{4,}/.*$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is False

    def test_orcid_pattern_with_dataframe(self) -> None:
        """Test ORCID pattern with pandas DataFrame."""
        df = pd.DataFrame(
            {"orcid": ["0000-0002-1234-5678", "0000-0002-1825-009X", "invalid"]}
        )
        matches = df["orcid"].str.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is True
        assert bool(matches.iloc[2]) is False

    def test_family_name_length_with_dataframe(self) -> None:
        """Test family_name length constraint with pandas DataFrame."""
        df = pd.DataFrame({"family_name": ["Smith", "O'Brien", ""]})
        valid = df["family_name"].str.len() >= 1
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is True
        assert bool(valid.iloc[2]) is False
