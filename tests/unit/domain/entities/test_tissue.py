"""Unit tests for Tissue domain entity."""

import pytest

from bioetl.domain.entities.chembl_tissue import Tissue


pytestmark = pytest.mark.unit

class TestTissue:
    """Tests for Tissue entity validation."""

    def test_valid_tissue_creation(self):
        """Test creating a valid Tissue entity."""
        tissue = Tissue(
            entity_id="chembl:tissue:CHEMBL3638177",
            content_hash="abc123",
            run_id="run_1",
            run_type="incremental",
            ingestion_ts="2023-01-01T00:00:00",
            _index=0,
            tissue_id="CHEMBL3638177",
            pref_name="Amniotic fluid",
            bto_id="BTO:0000068",
            caloha_id="TS-0034",
            efo_id=None,
            uberon_id="UBERON:0000173",
        )
        assert tissue.tissue_id == "CHEMBL3638177"
        assert tissue.pref_name == "Amniotic fluid"
        assert tissue.bto_id == "BTO:0000068"

    def test_tissue_requires_chembl_id(self):
        """Test that tissue_id is required."""
        with pytest.raises(ValueError, match="Tissue ChEMBL ID is required"):
            Tissue(
                entity_id="test",
                content_hash="abc",
                run_id="run_1",
                run_type="incremental",
                ingestion_ts="2023-01-01T00:00:00",
                _index=0,
                tissue_id="",  # Empty
                pref_name="Test",
            )

    def test_tissue_requires_pref_name(self):
        """Test that pref_name is required."""
        with pytest.raises(ValueError, match="Tissue pref_name is required"):
            Tissue(
                entity_id="test",
                content_hash="abc",
                run_id="run_1",
                run_type="incremental",
                ingestion_ts="2023-01-01T00:00:00",
                _index=0,
                tissue_id="CHEMBL123",
                pref_name="",  # Empty
            )

    def test_tissue_optional_fields_can_be_none(self):
        """Test that ontology IDs can be None."""
        tissue = Tissue(
            entity_id="test",
            content_hash="abc",
            run_id="run_1",
            run_type="incremental",
            ingestion_ts="2023-01-01T00:00:00",
            _index=0,
            tissue_id="CHEMBL123",
            pref_name="Test Tissue",
            bto_id=None,
            caloha_id=None,
            efo_id=None,
            uberon_id=None,
        )
        assert tissue.bto_id is None
        assert tissue.caloha_id is None

    def test_tissue_is_frozen(self):
        """Test that Tissue entity is immutable."""
        tissue = Tissue(
            entity_id="test",
            content_hash="abc",
            run_id="run_1",
            run_type="incremental",
            ingestion_ts="2023-01-01T00:00:00",
            _index=0,
            tissue_id="CHEMBL123",
            pref_name="Test",
        )
        with pytest.raises(AttributeError):
            tissue.pref_name = "Modified"  # type: ignore
