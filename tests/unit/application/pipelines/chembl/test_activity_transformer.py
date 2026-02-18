"""Unit tests for ActivityTransformer."""

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer


class TestActivityTransformer:
    """Tests for ActivityTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create transformer instance."""
        return ActivityTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self):
        """Sample ChEMBL API activity record."""
        return {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL204",
            "assay_chembl_id": "CHEMBL1000",
            "document_chembl_id": "CHEMBL1122",
            "record_id": 999,
            "src_id": 1,
            "canonical_smiles": "CCO",
            "molecule_pref_name": "Ethanol",
            "parent_molecule_chembl_id": "CHEMBL25",
            "target_pref_name": "Target A",
            "target_organism": "Homo sapiens",
            "target_tax_id": "9606",
            "assay_type": "B",
            "assay_description": "Binding assay",
            "bao_endpoint": "BAO_0000190",
            "bao_format": "BAO_0000219",
            "bao_label": "IC50",
            "type": "IC50",
            "value": "5.5",
            "units": "nM",
            "relation": "=",
            "standard_type": "IC50",
            "standard_value": "5.5",
            "standard_units": "nM",
            "standard_relation": "=",
            "pchembl_value": "8.26",
            "ligand_efficiency": {
                "bei": "18.5",
                "le": "0.45",
                "lle": "5.2",
                "sei": "12.1",
            },
            "action_type": {
                "action_type": "INHIBITOR",
                "description": "Inhibits target",
                "parent_type": "MODULATOR",
            },
            "activity_properties": [{"name": "prop1", "value": "val1"}],
        }

    def test_entity_class_is_bioactivity(self, transformer):
        """Test transformer uses Bioactivity entity class."""
        from bioetl.domain.entities import Bioactivity

        assert transformer.entity_class is Bioactivity

    def test_primary_id_field(self, transformer):
        """Test primary ID field is activity_id."""
        assert transformer.primary_id_field == "activity_id"

    def test_extract_business_data(self, transformer, sample_record):
        """Test business data extraction."""
        data = transformer._extract_business_data(
            sample_record,
            sample_record["activity_id"],
        )

        # Check identifiers
        assert data["activity_id"] == "12345"
        assert data["molecule_chembl_id"] == "CHEMBL25"
        assert data["target_chembl_id"] == "CHEMBL204"
        assert data["assay_chembl_id"] == "CHEMBL1000"
        assert data["document_chembl_id"] == "CHEMBL1122"
        assert data["record_id"] == 999
        assert data["src_id"] == 1

        # Check molecule/target/assay
        assert data["canonical_smiles"] == "CCO"
        assert data["molecule_pref_name"] == "Ethanol"
        assert data["target_pref_name"] == "Target A"
        assert data["target_organism"] == "Homo sapiens"
        assert data["target_taxonomy_id"] == "9606"
        assert data["assay_type"] == "B"
        assert data["assay_description"] == "Binding assay"

        # Check values
        assert data["type"] == "IC50"
        assert data["value"] == 5.5
        assert data["units"] == "nM"
        assert data["relation"] == "="
        assert data["standard_type"] == "IC50"
        assert data["standard_value"] == 5.5
        assert data["standard_units"] == "nM"
        assert data["pchembl_value"] == 8.26

        # Check nested extractions
        assert data["ligand_efficiency_bei"] == 18.5
        assert data["ligand_efficiency_le"] == 0.45
        assert data["action_type_action_type"] == "INHIBITOR"
        assert data["action_type_description"] == "Inhibits target"

        # Check JSON serialization
        assert "activity_properties" in data
        assert isinstance(data["activity_properties"], str)
        assert "prop1" in data["activity_properties"]

    def test_extract_ligand_efficiency_none(self, transformer):
        """Test ligand efficiency extraction with None."""
        result = transformer._extract_ligand_efficiency(None)
        assert result["ligand_efficiency_bei"] is None
        assert result["ligand_efficiency_le"] is None

    def test_extract_action_type_none(self, transformer):
        """Test action type extraction with None."""
        result = transformer._extract_action_type(None)
        assert result["action_type_action_type"] is None
        assert result["action_type_description"] is None
