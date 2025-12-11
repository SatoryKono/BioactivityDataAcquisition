"""Unit tests for ChemblRecordMapper."""

from pydantic import ValidationError
import pytest

from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    MoleculeRawModel,
    PublicationRawModel,
    TargetRawModel,
)
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry


class TestChemblRecordMapperActivityMapping:
    """Tests for activity record mapping."""

    def test_maps_valid_activity_record(self) -> None:
        """Valid activity dict is mapped to ActivityRawModel."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "activity_id": 12345,
                "standard_flag": True,
                "standard_value": 10.5,
                "assay_chembl_id": "CHEMBL123",
                "molecule_chembl_id": "CHEMBL456",
            }
        ]

        result = mapper.map_records(raw_records, "activity")

        assert len(result) == 1
        assert isinstance(result[0], ActivityRawModel)
        assert str(result[0].activity_id) == "12345"
        assert result[0].standard_flag is True
        assert str(result[0].assay_chembl_id) == "CHEMBL123"

    def test_maps_multiple_activity_records(self) -> None:
        """Multiple activity records are all mapped correctly."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {"activity_id": 1, "standard_flag": True, "standard_value": 1.0},
            {"activity_id": 2, "standard_flag": False},
            {"activity_id": 3, "standard_flag": True, "standard_value": 3.0},
        ]

        result = mapper.map_records(raw_records, "activity")

        assert len(result) == 3
        assert all(isinstance(r, ActivityRawModel) for r in result)
        assert [str(r.activity_id) for r in result] == ["1", "2", "3"]


class TestChemblRecordMapperMoleculeMapping:
    """Tests for molecule record mapping."""

    def test_maps_valid_molecule_record(self) -> None:
        """Valid molecule dict is mapped to MoleculeRawModel."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "molecule_chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "molecule_type": "Small molecule",
                "max_phase": 4,
            }
        ]

        result = mapper.map_records(raw_records, "molecule")

        assert len(result) == 1
        assert isinstance(result[0], MoleculeRawModel)
        assert str(result[0].molecule_chembl_id) == "CHEMBL25"
        assert result[0].pref_name == "ASPIRIN"
        assert result[0].max_phase == 4


class TestChemblRecordMapperTargetMapping:
    """Tests for target record mapping."""

    def test_maps_valid_target_record(self) -> None:
        """Valid target dict is mapped to TargetRawModel."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "target_chembl_id": "CHEMBL204",
                "pref_name": "Cyclooxygenase-2",
                "organism": "Homo sapiens",
                "target_type": "SINGLE PROTEIN",
                "tax_id": 9606,
            }
        ]

        result = mapper.map_records(raw_records, "target")

        assert len(result) == 1
        assert isinstance(result[0], TargetRawModel)
        assert str(result[0].target_chembl_id) == "CHEMBL204"
        assert result[0].organism == "Homo sapiens"
        assert result[0].tax_id == 9606


class TestChemblRecordMapperAssayMapping:
    """Tests for assay record mapping."""

    def test_maps_valid_assay_record(self) -> None:
        """Valid assay dict is mapped to AssayRawModel."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "assay_chembl_id": "CHEMBL1217643",
                "assay_type": "B",
                "description": "Binding assay",
                "assay_organism": "Homo sapiens",
            }
        ]

        result = mapper.map_records(raw_records, "assay")

        assert len(result) == 1
        assert isinstance(result[0], AssayRawModel)
        assert str(result[0].assay_chembl_id) == "CHEMBL1217643"
        assert result[0].assay_type == "B"
        assert result[0].description == "Binding assay"


class TestChemblRecordMapperDocumentMapping:
    """Tests for document record mapping."""

    def test_maps_valid_document_record(self) -> None:
        """Valid document dict is mapped to PublicationRawModel."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "document_chembl_id": "CHEMBL1125443",
                "journal": "J. Med. Chem.",
                "year": 2007,
                "pubmed_id": 17181143,
                "doi": "10.1021/jm0610232",
            }
        ]

        result = mapper.map_records(raw_records, "document")

        assert len(result) == 1
        assert isinstance(result[0], PublicationRawModel)
        assert str(result[0].document_chembl_id) == "CHEMBL1125443"
        assert result[0].journal == "J. Med. Chem."
        assert result[0].year == 2007
        assert result[0].pubmed_id == 17181143


class TestChemblRecordMapperUnknownEntity:
    """Tests for unknown entity handling."""

    def test_raises_value_error_for_unknown_entity(self) -> None:
        """ValueError is raised when entity type is not supported."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [{"id": 1}]

        with pytest.raises(ValueError, match="Unknown entity type: unknown"):
            mapper.map_records(raw_records, "unknown")

    def test_error_message_lists_supported_entities(self) -> None:
        """Error message includes list of supported entity types."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [{"id": 1}]

        with pytest.raises(ValueError) as exc_info:
            mapper.map_records(raw_records, "invalid_entity")

        error_msg = str(exc_info.value)
        assert "activity" in error_msg
        assert "molecule" in error_msg
        assert "target" in error_msg
        assert "assay" in error_msg
        assert "document" in error_msg


class TestChemblRecordMapperValidationError:
    """Tests for validation error handling."""

    def test_raises_validation_error_for_missing_required_field(self) -> None:
        """ValidationError is raised when required field is missing."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        # activity_id is required but missing
        raw_records = [{"standard_flag": True}]

        with pytest.raises(ValidationError):
            mapper.map_records(raw_records, "activity")

    def test_raises_validation_error_for_invalid_type(self) -> None:
        """ValidationError is raised when field has invalid type."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        # standard_flag must be bool
        raw_records = [
            {
                "activity_id": 1,
                "standard_flag": "not_a_boolean",
            }
        ]

        with pytest.raises(ValidationError):
            mapper.map_records(raw_records, "activity")

    def test_raises_validation_error_for_extra_fields_in_activity(self) -> None:
        """ValidationError is raised for extra fields in ActivityRawModel.

        ActivityRawModel uses extra='forbid' configuration.
        """
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        raw_records = [
            {
                "activity_id": 1,
                "standard_flag": True,
                "unknown_extra_field": "should_fail",
            }
        ]

        with pytest.raises(ValidationError):
            mapper.map_records(raw_records, "activity")


class TestChemblRecordMapperSupportedEntities:
    """Tests for get_supported_entities method."""

    def test_returns_frozenset(self) -> None:
        """Method returns a frozenset."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        result = mapper.get_supported_entities()
        assert isinstance(result, frozenset)

    def test_contains_all_entity_types(self) -> None:
        """Returned set contains all six entity types."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        supported = mapper.get_supported_entities()

        expected = {
            "activity",
            "molecule",
            "target",
            "assay",
            "document",
            "publication",
        }
        assert supported == expected

    def test_frozenset_is_immutable(self) -> None:
        """Returned frozenset cannot be modified."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        supported = mapper.get_supported_entities()

        with pytest.raises(AttributeError):
            supported.add("new_entity")  # type: ignore[attr-defined]


class TestChemblRecordMapperEmptyInput:
    """Tests for empty input handling."""

    def test_empty_list_returns_empty_list(self) -> None:
        """Empty input list returns empty output list."""
        mapper = ChemblRecordMapper(get_chembl_model_registry())
        result = mapper.map_records([], "activity")
        assert result == []
