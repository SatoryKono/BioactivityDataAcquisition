"""Tests for ChEMBL activity/assay Pydantic DTO models.

Tests for ActivityRecord and AssayRecord — frozen Pydantic models
with extra='forbid' to detect API changes early.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.domain.entities._chembl_activity_assay_models import (
    ActivityRecord,
    AssayRecord,
)


# ===========================================================================
# ActivityRecord tests
# ===========================================================================


@pytest.mark.unit
class TestActivityRecord:
    """Tests for ActivityRecord Pydantic DTO."""

    def test_valid_minimal_creation(self) -> None:
        """Test creation with only required fields."""
        record = ActivityRecord(
            activity_id="12345678",
            molecule_id="CHEMBL25",
        )
        assert record.activity_id == "12345678"
        assert record.molecule_id == "CHEMBL25"
        assert record.assay_id is None
        assert record.target_id is None
        assert record.standard_type is None
        assert record.standard_value is None
        assert record.pchembl_value is None

    def test_valid_full_creation(self) -> None:
        """Test creation with all core fields populated."""
        record = ActivityRecord(
            activity_id="12345678",
            molecule_id="CHEMBL25",
            assay_id="CHEMBL1000",
            target_id="CHEMBL204",
            publication_id="CHEMBL1125145",
            standard_type="IC50",
            standard_value=5.0,
            standard_units="nM",
            standard_relation="=",
            pchembl_value=8.3,
            action_type="INHIBITOR",
        )
        assert record.standard_type == "IC50"
        assert record.standard_value == pytest.approx(5.0)
        assert record.pchembl_value == pytest.approx(8.3)
        assert record.action_type == "INHIBITOR"

    def test_with_ligand_efficiency_metrics(self) -> None:
        """Test creation with ligand efficiency metrics."""
        record = ActivityRecord(
            activity_id="99999",
            molecule_id="CHEMBL100",
            ligand_efficiency_bei=23.5,
            ligand_efficiency_le=0.42,
            ligand_efficiency_lle=3.1,
            ligand_efficiency_sei=10.2,
        )
        assert record.ligand_efficiency_bei == pytest.approx(23.5)
        assert record.ligand_efficiency_le == pytest.approx(0.42)

    def test_with_target_info_denormalized(self) -> None:
        """Test creation with denormalized target fields."""
        record = ActivityRecord(
            activity_id="111",
            molecule_id="CHEMBL25",
            target_pref_name="EGFR",
            target_organism="Homo sapiens",
            target_tax_id="9606",
        )
        assert record.target_pref_name == "EGFR"
        assert record.target_tax_id == "9606"

    def test_missing_required_activity_id_raises(self) -> None:
        """Test missing activity_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ActivityRecord(molecule_id="CHEMBL25")  # type: ignore[call-arg]

    def test_missing_required_molecule_id_raises(self) -> None:
        """Test missing molecule_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ActivityRecord(activity_id="12345678")  # type: ignore[call-arg]

    def test_extra_field_forbidden(self) -> None:
        """Test extra fields raise ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ActivityRecord(
                activity_id="123",
                molecule_id="CHEMBL25",
                unknown_field="oops",  # type: ignore[call-arg]
            )

    def test_frozen_immutability(self) -> None:
        """Test that frozen model cannot be mutated."""
        record = ActivityRecord(activity_id="123", molecule_id="CHEMBL25")
        with pytest.raises(ValidationError):
            record.activity_id = "999"  # type: ignore[misc]

    def test_optional_fields_default_to_none(self) -> None:
        """Test all optional fields default to None."""
        record = ActivityRecord(activity_id="1", molecule_id="CHEMBL1")
        assert record.assay_id is None
        assert record.standard_type is None
        assert record.standard_value is None
        assert record.standard_units is None
        assert record.pchembl_value is None
        assert record.canonical_smiles is None
        assert record.bao_endpoint is None
        assert record.activity_properties is None

    def test_float_standard_value(self) -> None:
        """Test standard_value accepts float."""
        record = ActivityRecord(
            activity_id="1",
            molecule_id="CHEMBL1",
            standard_value=0.001,
        )
        assert record.standard_value == pytest.approx(0.001)

    def test_data_quality_fields(self) -> None:
        """Test data quality annotation fields."""
        record = ActivityRecord(
            activity_id="1",
            molecule_id="CHEMBL1",
            activity_comment="Inactive compound",
            data_validity_comment="Manually curated",
            potential_duplicate=0,
        )
        assert record.activity_comment == "Inactive compound"
        assert record.potential_duplicate == 0

    def test_model_dump(self) -> None:
        """Test model_dump returns correct dict."""
        record = ActivityRecord(
            activity_id="123",
            molecule_id="CHEMBL25",
            standard_type="IC50",
        )
        data = record.model_dump()
        assert data["activity_id"] == "123"
        assert data["molecule_id"] == "CHEMBL25"
        assert data["standard_type"] == "IC50"
        assert "assay_id" in data  # Optional fields present in dump


# ===========================================================================
# AssayRecord tests
# ===========================================================================


@pytest.mark.unit
class TestAssayRecord:
    """Tests for AssayRecord Pydantic DTO."""

    def test_valid_minimal_creation(self) -> None:
        """Test creation with only required field."""
        record = AssayRecord(assay_id="CHEMBL1000")
        assert record.assay_id == "CHEMBL1000"
        assert record.target_id is None
        assert record.assay_type is None
        assert record.confidence_score is None

    def test_valid_full_creation(self) -> None:
        """Test creation with all core fields populated."""
        record = AssayRecord(
            assay_id="CHEMBL1000",
            target_id="CHEMBL204",
            publication_id="CHEMBL1125145",
            assay_type="B",
            assay_type_description="Binding",
            assay_organism="Homo sapiens",
            assay_tax_id=9606,
            confidence_score=9,
            description="An in vitro binding assay",
        )
        assert record.assay_type == "B"
        assert record.assay_tax_id == 9606
        assert record.confidence_score == 9

    def test_with_variant_fields(self) -> None:
        """Test creation with variant information."""
        record = AssayRecord(
            assay_id="CHEMBL2000",
            variant_accession="Q9Y463",
            variant_mutation="V600E",
            variant_organism="Homo sapiens",
            variant_isoform="iso1",
        )
        assert record.variant_accession == "Q9Y463"
        assert record.variant_mutation == "V600E"

    def test_with_bao_annotations(self) -> None:
        """Test creation with BioAssay Ontology annotations."""
        record = AssayRecord(
            assay_id="CHEMBL3000",
            bao_format="BAO_0000019",
            bao_label="single protein format",
        )
        assert record.bao_format == "BAO_0000019"
        assert record.bao_label == "single protein format"

    def test_missing_required_assay_id_raises(self) -> None:
        """Test missing assay_id raises ValidationError."""
        with pytest.raises(ValidationError):
            AssayRecord()  # type: ignore[call-arg]

    def test_extra_field_forbidden(self) -> None:
        """Test extra fields raise ValidationError."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            AssayRecord(
                assay_id="CHEMBL1000",
                extra_unknown_field="bad",  # type: ignore[call-arg]
            )

    def test_frozen_immutability(self) -> None:
        """Test frozen model cannot be mutated."""
        record = AssayRecord(assay_id="CHEMBL1000")
        with pytest.raises(ValidationError):
            record.assay_id = "CHEMBL9999"  # type: ignore[misc]

    def test_optional_fields_default_to_none(self) -> None:
        """Test all optional fields default to None."""
        record = AssayRecord(assay_id="CHEMBL1000")
        assert record.target_id is None
        assert record.publication_id is None
        assert record.assay_type is None
        assert record.description is None
        assert record.assay_organism is None
        assert record.confidence_score is None
        assert record.assay_classifications is None
        assert record.assay_parameters is None

    def test_confidence_score_integer(self) -> None:
        """Test confidence_score accepts integer in range 0-9."""
        for score in [0, 5, 9]:
            record = AssayRecord(assay_id="CHEMBL1000", confidence_score=score)
            assert record.confidence_score == score

    def test_model_dump(self) -> None:
        """Test model_dump returns correct dict."""
        record = AssayRecord(
            assay_id="CHEMBL1000",
            assay_type="B",
            confidence_score=9,
        )
        data = record.model_dump()
        assert data["assay_id"] == "CHEMBL1000"
        assert data["assay_type"] == "B"
        assert data["confidence_score"] == 9

    def test_json_fields_as_string(self) -> None:
        """Test JSON-serialized fields are stored as strings."""
        import json

        classifications = json.dumps([{"level": "1", "class": "enzyme"}])
        record = AssayRecord(
            assay_id="CHEMBL1000",
            assay_classifications=classifications,
        )
        assert record.assay_classifications == classifications
        # Verify it is a valid JSON string
        loaded = json.loads(record.assay_classifications)
        assert isinstance(loaded, list)
