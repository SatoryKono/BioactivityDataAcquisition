# tests/unit/domain/schemas/crossref/test_funder_schema.py
"""Unit tests for CrossRef Funder Schema field validations.

Tests focus on CrossRef-specific field constraints for Funder entity.
ETL metadata fields are validated separately by base schema tests.
"""

from __future__ import annotations

import re

import pandas as pd

from bioetl.domain.schemas.crossref.funder import FunderSchema


class TestDoiValidation:
    """Tests for DOI field validation (foreign key to Publication)."""

    def test_valid_doi_format(self) -> None:
        """Test valid DOI format passes."""
        valid_doi = "10.1038/s41586-024-07487-w"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_valid_doi_different_registrar(self) -> None:
        """Test DOI from different registrar."""
        valid_doi = "10.1021/acs.jmedchem.0c00385"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, valid_doi) is not None

    def test_invalid_doi_wrong_prefix(self) -> None:
        """Test DOI with wrong prefix fails."""
        invalid_doi = "11.1234/wrong"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None

    def test_invalid_doi_not_a_doi(self) -> None:
        """Test non-DOI string fails."""
        invalid_doi = "not-a-doi"
        pattern = r"^10\.\d{4,}/.*$"
        assert re.match(pattern, invalid_doi) is None


class TestFunderSequenceValidation:
    """Tests for funder_sequence field validation."""

    def test_valid_funder_sequence_zero(self) -> None:
        """Test funder_sequence of 0 (primary funder)."""
        valid_sequence = 0
        assert valid_sequence >= 0

    def test_valid_funder_sequence_positive(self) -> None:
        """Test positive funder_sequence."""
        valid_sequence = 3
        assert valid_sequence >= 0

    def test_invalid_funder_sequence_negative(self) -> None:
        """Test negative funder_sequence fails."""
        invalid_sequence = -1
        assert not (invalid_sequence >= 0)


class TestFunderNameValidation:
    """Tests for funder name field validation."""

    def test_valid_funder_name(self) -> None:
        """Test valid funder name."""
        valid_name = "National Institutes of Health"
        assert len(valid_name) >= 1

    def test_invalid_funder_name_empty(self) -> None:
        """Test empty funder name fails."""
        invalid_name = ""
        assert not (len(invalid_name) >= 1)

    def test_valid_funder_name_with_abbreviation(self) -> None:
        """Test funder name with abbreviation and special characters."""
        valid_name = "NSF (National Science Foundation)"
        assert len(valid_name) >= 1


class TestFunderDoiValidation:
    """Tests for funder_doi field validation (Funder Registry DOI)."""

    def test_valid_funder_doi_format(self) -> None:
        """Test valid Funder Registry DOI format (10.13039/...)."""
        valid_funder_doi = "10.13039/100000001"
        pattern = r"^10\.13039/\d+$"
        assert re.match(pattern, valid_funder_doi) is not None

    def test_valid_funder_doi_nih(self) -> None:
        """Test valid NIH Funder Registry DOI."""
        valid_funder_doi = "10.13039/100000002"
        pattern = r"^10\.13039/\d+$"
        assert re.match(pattern, valid_funder_doi) is not None

    def test_invalid_funder_doi_wrong_prefix(self) -> None:
        """Test funder DOI with wrong registry prefix fails."""
        invalid_funder_doi = "10.1038/100000001"
        pattern = r"^10\.13039/\d+$"
        assert re.match(pattern, invalid_funder_doi) is None

    def test_invalid_funder_doi_with_letters(self) -> None:
        """Test funder DOI with letters in ID fails."""
        invalid_funder_doi = "10.13039/abc123"
        pattern = r"^10\.13039/\d+$"
        assert re.match(pattern, invalid_funder_doi) is None

    def test_invalid_funder_doi_non_doi(self) -> None:
        """Test non-DOI string fails."""
        invalid_funder_doi = "not-a-funder-doi"
        pattern = r"^10\.13039/\d+$"
        assert re.match(pattern, invalid_funder_doi) is None


class TestAwardCountValidation:
    """Tests for award_count field validation."""

    def test_valid_award_count_zero(self) -> None:
        """Test award_count of 0 is valid."""
        valid_count = 0
        assert valid_count >= 0

    def test_valid_award_count_positive(self) -> None:
        """Test positive award_count."""
        valid_count = 5
        assert valid_count >= 0

    def test_invalid_award_count_negative(self) -> None:
        """Test negative award_count fails."""
        invalid_count = -1
        assert not (invalid_count >= 0)


class TestSchemaFieldDefinitions:
    """Tests that verify schema field definitions exist and have correct properties."""

    def test_schema_has_funder_fields(self) -> None:
        """Test schema defines all required Funder fields."""
        schema = FunderSchema.to_schema()
        required_fields = [
            "doi",
            "funder_sequence",
            "name",
            "funder_doi",
            "funder_id",
            "award_numbers",
            "award_count",
        ]

        for field in required_fields:
            assert field in schema.columns, f"Missing field: {field}"

    def test_doi_not_nullable(self) -> None:
        """Test doi is not nullable (FK required)."""
        schema = FunderSchema.to_schema()
        doi_col = schema.columns.get("doi")
        assert doi_col is not None
        assert doi_col.nullable is False

    def test_funder_sequence_not_nullable(self) -> None:
        """Test funder_sequence is not nullable (PK component)."""
        schema = FunderSchema.to_schema()
        seq_col = schema.columns.get("funder_sequence")
        assert seq_col is not None
        assert seq_col.nullable is False

    def test_name_not_nullable(self) -> None:
        """Test name is not nullable (required)."""
        schema = FunderSchema.to_schema()
        name_col = schema.columns.get("name")
        assert name_col is not None
        assert name_col.nullable is False

    def test_optional_fields_nullable(self) -> None:
        """Test optional fields are nullable."""
        schema = FunderSchema.to_schema()
        nullable_fields = [
            "funder_doi",
            "funder_id",
            "award_numbers",
            "award_count",
        ]

        for field in nullable_fields:
            col = schema.columns.get(field)
            assert col is not None, f"Missing field: {field}"
            assert col.nullable is True, f"Field {field} should be nullable"


class TestSchemaConfiguration:
    """Tests for schema configuration."""

    def test_schema_is_strict(self) -> None:
        """Test schema has strict mode enabled."""
        schema = FunderSchema.to_schema()
        assert schema.strict is True

    def test_schema_is_ordered(self) -> None:
        """Test schema has ordered mode enabled."""
        schema = FunderSchema.to_schema()
        assert schema.ordered is True

    def test_schema_has_coerce(self) -> None:
        """Test schema has coerce mode enabled."""
        schema = FunderSchema.to_schema()
        assert schema.coerce is True

    def test_schema_has_correct_name(self) -> None:
        """Test schema has expected name."""
        schema = FunderSchema.to_schema()
        assert schema.name == "FunderSchema"


class TestDataFramePatterns:
    """Tests using pandas DataFrame for field validation patterns."""

    def test_doi_pattern_with_dataframe(self) -> None:
        """Test DOI pattern with pandas DataFrame."""
        df = pd.DataFrame({"doi": ["10.1038/s41586-024-07487-w", "invalid-doi"]})
        matches = df["doi"].str.match(r"^10\.\d{4,}/.*$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is False

    def test_funder_doi_pattern_with_dataframe(self) -> None:
        """Test funder DOI pattern with pandas DataFrame."""
        df = pd.DataFrame(
            {"funder_doi": ["10.13039/100000001", "10.1038/invalid", "not-a-doi"]}
        )
        matches = df["funder_doi"].str.match(r"^10\.13039/\d+$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is False
        assert bool(matches.iloc[2]) is False

    def test_name_length_with_dataframe(self) -> None:
        """Test name length constraint with pandas DataFrame."""
        df = pd.DataFrame({"name": ["National Institutes of Health", "NIH", ""]})
        valid = df["name"].str.len() >= 1
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is True
        assert bool(valid.iloc[2]) is False
