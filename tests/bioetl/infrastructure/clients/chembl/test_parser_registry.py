"""Tests for ChEMBL parser registry."""

import pytest

from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    DocumentRawModel,
    MoleculeRawModel,
    TargetRawModel,
)
from bioetl.infrastructure.clients.chembl.parser_registry import (
    ENTITY_MODEL_REGISTRY,
    get_model_for_entity,
    get_parser_for_entity,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
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

    def test_error_message_lists_available_entities(self):
        """Test that error message lists available entity types."""
        with pytest.raises(ValueError) as exc_info:
            get_model_for_entity("invalid")
        assert "Available:" in str(exc_info.value)


class TestGetParserForEntity:
    """Tests for get_parser_for_entity function."""

    @pytest.mark.parametrize(
        "entity", ["activity", "molecule", "target", "assay", "document"]
    )
    def test_returns_parser_instance(self, entity):
        """Test that function returns ChemblResponseParserImpl instance."""
        parser = get_parser_for_entity(entity)
        assert isinstance(parser, ChemblResponseParserImpl)

    def test_activity_parser_parses_activities(self):
        """Test that activity parser correctly parses activities."""
        parser = get_parser_for_entity("activity")
        response = {
            "activities": [
                {"activity_id": "1", "standard_flag": True},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], ActivityRawModel)

    def test_molecule_parser_parses_molecules(self):
        """Test that molecule parser correctly parses molecules."""
        parser = get_parser_for_entity("molecule")
        response = {
            "molecules": [
                {"molecule_chembl_id": "CHEMBL1"},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], MoleculeRawModel)

    def test_target_parser_parses_targets(self):
        """Test that target parser correctly parses targets."""
        parser = get_parser_for_entity("target")
        response = {
            "targets": [
                {"target_chembl_id": "CHEMBL1234"},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], TargetRawModel)

    def test_assay_parser_parses_assays(self):
        """Test that assay parser correctly parses assays."""
        parser = get_parser_for_entity("assay")
        response = {
            "assays": [
                {"assay_chembl_id": "CHEMBL1000"},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], AssayRawModel)

    def test_document_parser_parses_documents(self):
        """Test that document parser correctly parses documents."""
        parser = get_parser_for_entity("document")
        response = {
            "documents": [
                {"document_chembl_id": "CHEMBL_DOC_1"},
            ],
        }
        records = parser.parse(response)
        assert len(records) == 1
        assert isinstance(records[0], DocumentRawModel)

    def test_raises_for_unknown_entity(self):
        """Test that function raises ValueError for unknown entity."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            get_parser_for_entity("unknown")
