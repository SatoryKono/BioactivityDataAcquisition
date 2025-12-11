"""Tests for ChEMBL entity model registry (infrastructure layer)."""

import pytest

from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.schemas.chembl.raw_models import (
    ActivityRawModel,
    AssayRawModel,
    MoleculeRawModel,
    PublicationRawModel,
    TargetRawModel,
)
from bioetl.infrastructure.chembl.model_registry import (
    ChemblEntityModelRegistry,
    get_chembl_model_registry,
)


class TestChemblEntityModelRegistry:
    """Tests for ChemblEntityModelRegistry."""

    def test_implements_abc(self):
        """Test that registry implements EntityModelRegistryABC."""
        registry = ChemblEntityModelRegistry()
        assert isinstance(registry, EntityModelRegistryABC)

    def test_supported_entities_contains_all_types(self):
        """Test that registry supports all expected entity types."""
        registry = ChemblEntityModelRegistry()
        expected_entities = {
            "activity",
            "molecule",
            "target",
            "assay",
            "document",
            "publication",
        }
        assert registry.supported_entities() == expected_entities

    def test_supported_entities_returns_frozenset(self):
        """Test that supported_entities returns a frozenset."""
        registry = ChemblEntityModelRegistry()
        result = registry.supported_entities()
        assert isinstance(result, frozenset)

    def test_get_model_returns_correct_models(self):
        """Test that get_model returns correct model classes."""
        registry = ChemblEntityModelRegistry()
        assert registry.get_model("activity") is ActivityRawModel
        assert registry.get_model("molecule") is MoleculeRawModel
        assert registry.get_model("target") is TargetRawModel
        assert registry.get_model("assay") is AssayRawModel
        assert registry.get_model("document") is PublicationRawModel
        assert registry.get_model("publication") is PublicationRawModel

    def test_get_model_raises_for_unknown_entity(self):
        """Test that get_model raises ValueError for unknown entity."""
        registry = ChemblEntityModelRegistry()
        with pytest.raises(ValueError, match="Unknown entity type: unknown"):
            registry.get_model("unknown")

    def test_error_message_lists_supported_entities(self):
        """Test that error message lists supported entity types."""
        registry = ChemblEntityModelRegistry()
        with pytest.raises(ValueError) as exc_info:
            registry.get_model("invalid")
        assert "Supported:" in str(exc_info.value)
        assert "activity" in str(exc_info.value)

    def test_is_supported_returns_true_for_supported(self):
        """Test is_supported returns True for supported entities."""
        registry = ChemblEntityModelRegistry()
        for entity in [
            "activity",
            "molecule",
            "target",
            "assay",
            "document",
            "publication",
        ]:
            assert registry.is_supported(entity) is True

    def test_is_supported_returns_false_for_unsupported(self):
        """Test is_supported returns False for unsupported entities."""
        registry = ChemblEntityModelRegistry()
        for entity in ["unknown", "invalid", "", "ACTIVITY", "Activity"]:
            assert registry.is_supported(entity) is False


class TestGetChemblModelRegistry:
    """Tests for get_chembl_model_registry factory function."""

    def test_returns_registry_instance(self):
        """Test that factory returns ChemblEntityModelRegistry instance."""
        registry = get_chembl_model_registry()
        assert isinstance(registry, ChemblEntityModelRegistry)

    def test_returns_same_instance(self):
        """Test that factory returns singleton instance."""
        registry1 = get_chembl_model_registry()
        registry2 = get_chembl_model_registry()
        assert registry1 is registry2


class TestModelValidation:
    """Tests that models can actually validate data."""

    @pytest.fixture
    def registry(self):
        """Provide a registry instance."""
        return ChemblEntityModelRegistry()

    def test_activity_model_validates_data(self, registry):
        """Test that ActivityRawModel can validate activity data."""
        model_class = registry.get_model("activity")
        data = {"activity_id": "1", "standard_flag": True, "standard_value": 1.0}
        instance = model_class.model_validate(data)
        assert str(instance.activity_id) == "1"

    def test_molecule_model_validates_data(self, registry):
        """Test that MoleculeRawModel can validate molecule data."""
        model_class = registry.get_model("molecule")
        data = {"molecule_chembl_id": "CHEMBL1"}
        instance = model_class.model_validate(data)
        assert str(instance.molecule_chembl_id) == "CHEMBL1"

    def test_target_model_validates_data(self, registry):
        """Test that TargetRawModel can validate target data."""
        model_class = registry.get_model("target")
        data = {"target_chembl_id": "CHEMBL1234"}
        instance = model_class.model_validate(data)
        assert str(instance.target_chembl_id) == "CHEMBL1234"

    def test_assay_model_validates_data(self, registry):
        """Test that AssayRawModel can validate assay data."""
        model_class = registry.get_model("assay")
        data = {"assay_chembl_id": "CHEMBL1000"}
        instance = model_class.model_validate(data)
        assert str(instance.assay_chembl_id) == "CHEMBL1000"

    def test_document_model_validates_data(self, registry):
        """Test that PublicationRawModel can validate document data."""
        model_class = registry.get_model("document")
        data = {"document_chembl_id": "CHEMBL123456"}
        instance = model_class.model_validate(data)
        assert str(instance.document_chembl_id) == "CHEMBL123456"

    def test_publication_model_validates_data(self, registry):
        """Test PublicationRawModel validates via publication alias."""
        model_class = registry.get_model("publication")
        data = {"document_chembl_id": "CHEMBL123456"}
        instance = model_class.model_validate(data)
        assert str(instance.document_chembl_id) == "CHEMBL123456"
