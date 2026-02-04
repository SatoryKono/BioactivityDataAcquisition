"""Unit tests for TissueTransformer."""

import pytest
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer
from bioetl.domain.context import PipelineContext


class TestTissueTransformer:
    """Tests for TissueTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return TissueTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self):
        """Sample ChEMBL API tissue record."""
        return {
            "tissue_chembl_id": "CHEMBL3638177",
            "pref_name": "Amniotic fluid",
            "bto_id": "BTO:0000068",
            "caloha_id": "TS-0034",
            "efo_id": None,
            "uberon_id": "UBERON:0000173",
        }

    def test_entity_class_is_tissue(self, transformer):
        """Test transformer uses Tissue entity class."""
        from bioetl.domain.entities.chembl_tissue import Tissue

        assert transformer.entity_class is Tissue

    def test_primary_id_field(self, transformer):
        """Test primary ID field is tissue_chembl_id."""
        assert transformer.primary_id_field == "tissue_chembl_id"

    def test_extract_business_data(self, transformer, sample_record):
        """Test business data extraction."""
        data = transformer._extract_business_data(
            sample_record,
            sample_record["tissue_chembl_id"],
        )

        assert data["tissue_chembl_id"] == "CHEMBL3638177"
        assert data["pref_name"] == "Amniotic fluid"
        assert data["bto_id"] == "BTO:0000068"
        assert data["caloha_id"] == "TS-0034"
        assert data["efo_id"] is None
        assert data["uberon_id"] == "UBERON:0000173"

    def test_extract_business_data_with_whitespace(self, transformer):
        """Test whitespace normalization."""
        record = {
            "tissue_chembl_id": "CHEMBL123",
            "pref_name": "  Test Tissue  ",
            "bto_id": "  BTO:0000001  ",
        }
        data = transformer._extract_business_data(record, "CHEMBL123")

        assert data["pref_name"] == "Test Tissue"
        assert data["bto_id"] == "BTO:0000001"
