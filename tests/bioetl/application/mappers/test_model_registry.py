"""Tests for ChEMBL model registry (application layer)."""

import pytest

from bioetl.application.mappers.chembl.model_registry import (
    ENTITY_MODEL_REGISTRY,
    get_model_for_entity,
    is_registered_entity,
)
from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)


class TestEntityModelRegistry:
    """Tests for ENTITY_MODEL_REGISTRY."""

    def test_registry_contains_all_entity_types(self):
        """Test that registry contains all expected entity types."""
        expected_entities = ["activity", "molecule", "target", "assay", "document"]
        for entity in expected_entities:
            assert entity in ENTITY_MODEL_REGISTRY

    def test_registry_maps_to_correct_models(self):
        """Test that registry maps entities to correct model classes."""
        assert ENTITY_MODEL_REGISTRY["activity"] is ActivityRawModel
        assert ENTITY_MODEL_REGISTRY["molecule"] is MoleculeRawModel
        assert ENTITY_MODEL_REGISTRY["target"] is TargetRawModel
        assert ENTITY_MODEL_REGISTRY["assay"] is AssayRawModel
        assert ENTITY_MODEL_REGISTRY["document"] is DocumentRawModel

    def test_registry_count(self):
        """Test that registry has exactly 5 entity types."""
        assert len(ENTITY_MODEL_REGISTRY) == 5


class TestGetModelForEntity:
    """Tests for get_model_for_entity function."""

    @pytest.mark.parametrize(
        "entity,expected_model",
        [
            ("activity", ActivityRawModel),
            ("molecule", MoleculeRawModel),
            ("target", TargetRawModel),
            ("assay", AssayRawModel),
            ("document", DocumentRawModel),
        ],
    )
    def test_returns_correct_model(self, entity, expected_model):
        """Test that function returns correct model for each entity."""
        assert get_model_for_entity(entity) is expected_model

    def test_raises_for_unknown_entity(self):
        """Test that function raises ValueError for unknown entity."""
        with pytest.raises(ValueError, match="Unknown entity type: unknown"):
            get_model_for_entity("unknown")

    def test_error_message_lists_supported_entities(self):
        """Test that error message lists supported entity types."""
        with pytest.raises(ValueError) as exc_info:
            get_model_for_entity("invalid")
        assert "Supported:" in str(exc_info.value)

    def test_error_message_contains_entity_names(self):
        """Test that error message contains entity names."""
        with pytest.raises(ValueError) as exc_info:
            get_model_for_entity("invalid")
        error_msg = str(exc_info.value)
        # Should contain sorted entity names
        assert "activity" in error_msg


class TestIsRegisteredEntity:
    """Tests for is_registered_entity function."""

    @pytest.mark.parametrize(
        "entity",
        ["activity", "molecule", "target", "assay", "document"],
    )
    def test_returns_true_for_registered_entities(self, entity):
        """Test that function returns True for registered entities."""
        assert is_registered_entity(entity) is True

    @pytest.mark.parametrize(
        "entity",
        ["unknown", "invalid", "", "ACTIVITY", "Activity"],
    )
    def test_returns_false_for_unregistered_entities(self, entity):
        """Test that function returns False for unregistered entities."""
        assert is_registered_entity(entity) is False


class TestModelValidation:
    """Tests that models can actually validate data."""

    def test_activity_model_validates_data(self):
        """Test that ActivityRawModel can validate activity data."""
        model_class = get_model_for_entity("activity")
        data = {"activity_id": "1", "standard_flag": True}
        instance = model_class.model_validate(data)
        assert instance.activity_id == "1"

    def test_molecule_model_validates_data(self):
        """Test that MoleculeRawModel can validate molecule data."""
        model_class = get_model_for_entity("molecule")
        data = {"molecule_chembl_id": "CHEMBL1"}
        instance = model_class.model_validate(data)
        assert instance.molecule_chembl_id == "CHEMBL1"

    def test_target_model_validates_data(self):
        """Test that TargetRawModel can validate target data."""
        model_class = get_model_for_entity("target")
        data = {"target_chembl_id": "CHEMBL1234"}
        instance = model_class.model_validate(data)
        assert instance.target_chembl_id == "CHEMBL1234"

    def test_assay_model_validates_data(self):
        """Test that AssayRawModel can validate assay data."""
        model_class = get_model_for_entity("assay")
        data = {"assay_chembl_id": "CHEMBL1000"}
        instance = model_class.model_validate(data)
        assert instance.assay_chembl_id == "CHEMBL1000"

    def test_document_model_validates_data(self):
        """Test that DocumentRawModel can validate document data."""
        model_class = get_model_for_entity("document")
        data = {"document_chembl_id": "CHEMBL_DOC_1"}
        instance = model_class.model_validate(data)
        assert instance.document_chembl_id == "CHEMBL_DOC_1"
