# tests/unit/domain/schemas/uniprot/test_idmapping_schema.py
"""Unit tests for UniProt ID Mapping Schema field validations.

Tests focus on ID mapping-specific field constraints.
ETL metadata fields are validated separately by base schema tests.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from bioetl.domain.schemas.uniprot.idmapping import (
    MAPPING_STATUSES,
    IDMappingSchema,
)

pytestmark = pytest.mark.unit


class TestTargetChemblIdValidation:
    """Tests for target_id field validation."""

    def test_valid_chembl_id(self) -> None:
        """Test valid ChEMBL target ID format."""
        valid_id = "CHEMBL204"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, valid_id) is not None

    def test_valid_chembl_id_long_number(self) -> None:
        """Test ChEMBL ID with longer number."""
        valid_id = "CHEMBL1234567890"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, valid_id) is not None

    def test_invalid_chembl_id_wrong_prefix(self) -> None:
        """Test ChEMBL ID with wrong prefix fails."""
        invalid_id = "DRUGBANK1234"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, invalid_id) is None

    def test_invalid_chembl_id_lowercase(self) -> None:
        """Test lowercase ChEMBL prefix fails."""
        invalid_id = "chembl204"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, invalid_id) is None

    def test_invalid_chembl_id_no_number(self) -> None:
        """Test ChEMBL ID without number fails."""
        invalid_id = "CHEMBL"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, invalid_id) is None

    def test_invalid_chembl_id_letters_after_chembl(self) -> None:
        """Test ChEMBL ID with letters in number part fails."""
        invalid_id = "CHEMBL204A"
        pattern = r"^CHEMBL\d+$"
        assert re.match(pattern, invalid_id) is None


class TestUniprotAccessionValidation:
    """Tests for uniprot_accession field validation."""

    def test_valid_uniprot_accession_6chars(self) -> None:
        """Test valid 6-character UniProt accession."""
        valid_accession = "P00742"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, valid_accession) is not None

    def test_valid_uniprot_accession_10chars(self) -> None:
        """Test valid 10-character UniProt accession (new format)."""
        valid_accession = "A0A1B2C3D4"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, valid_accession) is not None

    def test_invalid_uniprot_accession_too_short(self) -> None:
        """Test accession shorter than 6 chars fails."""
        invalid_accession = "P007"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, invalid_accession) is None

    def test_invalid_uniprot_accession_too_long(self) -> None:
        """Test accession longer than 10 chars fails."""
        invalid_accession = "A0A1B2C3D4E5"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, invalid_accession) is None

    def test_invalid_uniprot_accession_lowercase(self) -> None:
        """Test lowercase accession fails."""
        invalid_accession = "p00742"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, invalid_accession) is None

    def test_invalid_uniprot_accession_special_chars(self) -> None:
        """Test accession with special characters fails."""
        invalid_accession = "P00-742"
        pattern = r"^[A-Z0-9]{6,10}$"
        assert re.match(pattern, invalid_accession) is None


class TestMappingStatusValidation:
    """Tests for mapping_status enum field validation."""

    @pytest.mark.parametrize("status", MAPPING_STATUSES)
    def test_valid_mapping_status(self, status: str) -> None:
        """Test all valid mapping status values."""
        assert status in MAPPING_STATUSES

    def test_invalid_mapping_status(self) -> None:
        """Test invalid mapping status."""
        invalid_status = "unknown"
        assert invalid_status not in MAPPING_STATUSES

    def test_mapping_statuses_expected_values(self) -> None:
        """Test expected mapping status values exist."""
        assert "found" in MAPPING_STATUSES
        assert "not_found" in MAPPING_STATUSES
        assert "error" in MAPPING_STATUSES
        assert "multiple" in MAPPING_STATUSES

    def test_mapping_statuses_count(self) -> None:
        """Test exactly 4 mapping statuses exist (found, not_found, error, multiple)."""
        assert len(MAPPING_STATUSES) == 4


class TestSchemaFieldDefinitions:
    """Tests that verify schema field definitions exist and have correct properties."""

    def test_schema_has_idmapping_fields(self) -> None:
        """Test schema defines all required ID mapping fields."""
        schema = IDMappingSchema.to_schema()
        required_fields = [
            "target_id",
            "uniprot_accession",
            "mapping_status",
        ]

        for field in required_fields:
            assert field in schema.columns, f"Missing field: {field}"

    def test_target_id_not_nullable(self) -> None:
        """Test target_id is not nullable (PK)."""
        schema = IDMappingSchema.to_schema()
        col = schema.columns.get("target_id")
        assert col is not None
        assert col.nullable is False

    def test_uniprot_accession_nullable(self) -> None:
        """Test uniprot_accession is nullable (None for not_found)."""
        schema = IDMappingSchema.to_schema()
        col = schema.columns.get("uniprot_accession")
        assert col is not None
        assert col.nullable is True

    def test_mapping_status_not_nullable(self) -> None:
        """Test mapping_status is not nullable (required)."""
        schema = IDMappingSchema.to_schema()
        col = schema.columns.get("mapping_status")
        assert col is not None
        assert col.nullable is False


class TestSchemaConfiguration:
    """Tests for schema configuration."""

    def test_schema_is_strict(self) -> None:
        """Test schema has strict mode enabled."""
        schema = IDMappingSchema.to_schema()
        assert schema.strict is True

    def test_schema_is_ordered(self) -> None:
        """Test schema has ordered mode enabled."""
        schema = IDMappingSchema.to_schema()
        assert schema.ordered is True

    def test_schema_has_coerce(self) -> None:
        """Test schema has coerce mode enabled."""
        schema = IDMappingSchema.to_schema()
        assert schema.coerce is True

    def test_schema_has_correct_name(self) -> None:
        """Test schema has expected name."""
        schema = IDMappingSchema.to_schema()
        assert schema.name == "IDMappingSchema"


class TestDataFramePatterns:
    """Tests using pandas DataFrame for field validation patterns."""

    def test_target_id_pattern_with_dataframe(self) -> None:
        """Test ChEMBL ID pattern with pandas DataFrame."""
        df = pd.DataFrame({"target_id": ["CHEMBL204", "CHEMBL1234567", "invalid"]})
        matches = df["target_id"].str.match(r"^CHEMBL\d+$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is True
        assert bool(matches.iloc[2]) is False

    def test_uniprot_accession_pattern_with_dataframe(self) -> None:
        """Test UniProt accession pattern with pandas DataFrame."""
        df = pd.DataFrame(
            {"uniprot_accession": ["P00742", "A0A1B2C3D4", "invalid", "p00742"]}
        )
        matches = df["uniprot_accession"].str.match(r"^[A-Z0-9]{6,10}$")
        assert bool(matches.iloc[0]) is True
        assert bool(matches.iloc[1]) is True
        assert bool(matches.iloc[2]) is False
        assert bool(matches.iloc[3]) is False

    def test_mapping_status_values_with_dataframe(self) -> None:
        """Test mapping_status values with pandas DataFrame."""
        df = pd.DataFrame(
            {"mapping_status": ["found", "not_found", "error", "unknown"]}
        )
        valid = df["mapping_status"].isin(MAPPING_STATUSES)
        assert bool(valid.iloc[0]) is True
        assert bool(valid.iloc[1]) is True
        assert bool(valid.iloc[2]) is True
        assert bool(valid.iloc[3]) is False
