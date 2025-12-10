"""Tests for ChEMBL parser registry."""

import pytest

from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.parser_registry import (
    SUPPORTED_ENTITIES,
    get_parser_for_entity,
    is_supported_entity,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


class TestSupportedEntities:
    """Tests for SUPPORTED_ENTITIES."""

    def test_supported_entities_contains_all_entity_types(self):
        """Test that SUPPORTED_ENTITIES contains all expected entity types."""
        expected_entities = ["activity", "molecule", "target", "assay", "document"]
        for entity in expected_entities:
            assert entity in SUPPORTED_ENTITIES

    def test_supported_entities_is_frozenset(self):
        """Test that SUPPORTED_ENTITIES is a frozenset (immutable)."""
        assert isinstance(SUPPORTED_ENTITIES, frozenset)

    def test_supported_entities_count(self):
        """Test that SUPPORTED_ENTITIES has exactly 5 entities."""
        assert len(SUPPORTED_ENTITIES) == 5


class TestIsSupportedEntity:
    """Tests for is_supported_entity function."""

    @pytest.mark.parametrize(
        "entity",
        ["activity", "molecule", "target", "assay", "document"],
    )
    def test_returns_true_for_supported_entities(self, entity):
        """Test that function returns True for supported entities."""
        assert is_supported_entity(entity) is True

    @pytest.mark.parametrize(
        "entity",
        ["unknown", "invalid", "", "ACTIVITY", "Activity"],
    )
    def test_returns_false_for_unsupported_entities(self, entity):
        """Test that function returns False for unsupported entities."""
        assert is_supported_entity(entity) is False


class TestGetParserForEntity:
    """Tests for get_parser_for_entity function."""

    @pytest.mark.parametrize(
        "entity", ["activity", "molecule", "target", "assay", "document"]
    )
    def test_returns_generic_parser_instance(self, entity):
        """Test that function returns ChemblGenericResponseParser instance."""
        parser = get_parser_for_entity(entity)
        assert isinstance(parser, ChemblGenericResponseParser)
        assert isinstance(parser, ResponseParserPortABC)

    def test_activity_parser_parses_activities(self):
        """Test that parser correctly parses activities."""
        parser = get_parser_for_entity("activity")
        response = {
            "activities": [
                {"activity_id": "1", "standard_flag": True},
            ],
        }
        records = parser.parse_to_records(response)
        assert len(records) == 1
        assert records[0]["activity_id"] == "1"

    def test_molecule_parser_parses_molecules(self):
        """Test that parser correctly parses molecules."""
        parser = get_parser_for_entity("molecule")
        response = {
            "molecules": [
                {"molecule_chembl_id": "CHEMBL1"},
            ],
        }
        records = parser.parse_to_records(response)
        assert len(records) == 1
        assert records[0]["molecule_chembl_id"] == "CHEMBL1"

    def test_target_parser_parses_targets(self):
        """Test that parser correctly parses targets."""
        parser = get_parser_for_entity("target")
        response = {
            "targets": [
                {"target_chembl_id": "CHEMBL1234"},
            ],
        }
        records = parser.parse_to_records(response)
        assert len(records) == 1
        assert records[0]["target_chembl_id"] == "CHEMBL1234"

    def test_assay_parser_parses_assays(self):
        """Test that parser correctly parses assays."""
        parser = get_parser_for_entity("assay")
        response = {
            "assays": [
                {"assay_chembl_id": "CHEMBL1000"},
            ],
        }
        records = parser.parse_to_records(response)
        assert len(records) == 1
        assert records[0]["assay_chembl_id"] == "CHEMBL1000"

    def test_document_parser_parses_documents(self):
        """Test that parser correctly parses documents."""
        parser = get_parser_for_entity("document")
        response = {
            "documents": [
                {"document_chembl_id": "CHEMBL_DOC_1"},
            ],
        }
        records = parser.parse_to_records(response)
        assert len(records) == 1
        assert records[0]["document_chembl_id"] == "CHEMBL_DOC_1"

    def test_raises_for_unknown_entity(self):
        """Test that function raises ValueError for unknown entity."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            get_parser_for_entity("unknown")

    def test_error_message_lists_supported_entities(self):
        """Test that error message lists supported entity types."""
        with pytest.raises(ValueError) as exc_info:
            get_parser_for_entity("invalid")
        assert "Supported:" in str(exc_info.value)


class TestDeprecatedApiAccessHandler:
    """Tests for deprecated API access handler."""

    def test_get_model_for_entity_raises_import_error(self):
        """Test that get_model_for_entity raises ImportError with helpful message."""
        # Use __getattr__ mechanism directly since importing would fail
        import bioetl.infrastructure.clients.chembl.parser_registry as pr

        with pytest.raises(ImportError) as exc_info:
            _ = pr.get_model_for_entity  # noqa: B018
        assert "moved to application layer" in str(exc_info.value)
        assert "model_registry" in str(exc_info.value)

    def test_entity_model_registry_raises_import_error(self):
        """Test that ENTITY_MODEL_REGISTRY raises ImportError with helpful message."""
        import bioetl.infrastructure.clients.chembl.parser_registry as pr

        with pytest.raises(ImportError) as exc_info:
            _ = pr.ENTITY_MODEL_REGISTRY  # noqa: B018
        assert "moved to application layer" in str(exc_info.value)
        assert "model_registry" in str(exc_info.value)

    def test_unknown_attribute_raises_attribute_error(self):
        """Test that unknown attributes raise AttributeError."""
        import bioetl.infrastructure.clients.chembl.parser_registry as pr

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = pr.unknown_attribute  # noqa: B018
