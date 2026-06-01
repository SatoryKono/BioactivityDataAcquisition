"""Unit tests for PubChem Compound transformer."""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.transformations import safe_float
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPubChemCompoundTransformer:
    """Tests for PubChemCompoundTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create PubChemCompoundTransformer instance."""
        return instantiate_test_transformer(
            PubChemCompoundTransformer,
            provider="pubchem",
        )

    @pytest.mark.asyncio
    async def test_compound_transformer__valid_record__a1346563(self, transformer, mock_context):
        """Test transformation of valid compound record with all fields."""
        record = {
            "molecule_id": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.16",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetoxybenzoic amolecule_id",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "2244"
        assert result["molecular_formula"] == "C9H8O4"
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert result["standardized_canonical_smiles"] == ("CC(=O)OC1=CC=CC=C1C(=O)O")
        assert result["standardized_inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert result["structure_parent_key"] == "inchikey14:BSYNRYMUTXBXSQ"
        assert result["chemical_standardization_status"] == "standardized"
        assert result["chemical_standardization_policy_version"] == "pubchem-basic-v1"
        assert result["chemical_standardization_warnings"] is None
        assert "entity_id" in result
        assert "content_hash" in result
        # Lineage fields should be present
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id_returns_none(
        self, transformer, mock_context
    ):
        """Missing molecule_id should return None with warning logged."""
        record = {
            "molecular_formula": "C9H8O4",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_missing_structural_identifiers(
        self, transformer, mock_context
    ):
        """Test transformation returns None when no structural identifiers present.

        Compound entity invariant requires at least one of:
        canonical_smiles, isomeric_smiles, or inchi.
        """
        record = {
            "molecule_id": 12345,
            "molecular_formula": "C10H12O2",
            "iupac_name": "Some compound",
            # Missing: canonical_smiles, isomeric_smiles, inchi
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_transform_with_only_canonical_smiles(
        self, transformer, mock_context
    ):
        """Test transformation succeeds with only canonical_smiles."""
        record = {
            "molecule_id": 12345,
            "canonical_smiles": "CCO",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "12345"
        assert result["canonical_smiles"] == "CCO"
        assert result["standardized_canonical_smiles"] == "CCO"
        assert result["chemical_standardization_status"] == "partial"
        assert json.loads(result["chemical_standardization_warnings"]) == [
            "parent_key_from_smiles_without_inchi_key"
        ]

    @pytest.mark.asyncio
    async def test_transform_with_only_isomeric_smiles(self, transformer, mock_context):
        """Test transformation succeeds with only isomeric_smiles."""
        record = {
            "molecule_id": 12345,
            "isomeric_smiles": "C[C@H](O)CC",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "12345"
        assert result["isomeric_smiles"] == "C[C@H](O)CC"

    @pytest.mark.asyncio
    async def test_transform_with_only_inchi(self, transformer, mock_context):
        """Test transformation succeeds with only inchi."""
        record = {
            "molecule_id": 12345,
            "inchi": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "12345"
        assert result["inchi"] == "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"

    @pytest.mark.asyncio
    async def test_transform_with_minimal_valid_record(self, transformer, mock_context):
        """Test transformation with minimal valid record (molecule_id + one structural ID)."""
        record = {
            "molecule_id": 1,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "1"
        assert result["canonical_smiles"] == "C"
        assert result.get("molecular_formula") is None
        assert result.get("molecular_weight") is None
        assert result.get("inchi_key") is None

    @pytest.mark.asyncio
    async def test_transform_molecule_id_converted_to_string(
        self, transformer, mock_context
    ):
        """Test that numeric molecule_id is converted to string."""
        record = {
            "molecule_id": 99999999,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "99999999"
        assert isinstance(result["molecule_id"], str)

    @pytest.mark.asyncio
    async def test_compound_transformer__entity_id_format__18df995f(self, transformer, mock_context):
        """Test that entity_id follows expected format."""
        record = {
            "molecule_id": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result
        # Entity ID should contain provider and molecule_id
        assert "pubchem" in result["entity_id"]
        assert "2244" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_content_hash_generated(self, transformer, mock_context):
        """Test that content_hash is generated and is consistent."""
        record = {
            "molecule_id": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result1 = await transformer.transform(mock_context, record, index=0)
        result2 = await transformer.transform(mock_context, record, index=0)

        assert result1 is not None
        assert result2 is not None
        assert "content_hash" in result1
        assert "content_hash" in result2
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_compound_transformer__staged_payload__58cb8c60(
        self, transformer, mock_context
    ):
        """Test staged PubChem path returns business data before hash finalization."""
        record = {
            "molecule_id": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == "pubchem:2244"
        assert result.business_data["molecule_id"] == "2244"
        assert result.business_data["chemical_standardization_status"] == "partial"
        assert result.business_data["standardized_canonical_smiles"] == (
            "CC(=O)OC1=CC=CC=C1C(=O)O"
        )
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_transform_reports_invalid_standardization_inputs(
        self, transformer, mock_context
    ):
        """Invalid structural identifiers are visible in standardization warnings."""
        record = {
            "molecule_id": 12345,
            "canonical_smiles": " CCO ",
            "inchi_key": "not-an-inchikey",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["canonical_smiles"] == "CCO"
        assert result["standardized_canonical_smiles"] == "CCO"
        assert result["standardized_inchi_key"] is None
        assert result["chemical_standardization_status"] == "partial"
        assert json.loads(result["chemical_standardization_warnings"]) == [
            "inchi_key_invalid",
            "parent_key_from_smiles_without_inchi_key",
        ]

    @pytest.mark.asyncio
    async def test_transform_reports_multi_component_parent_deferred(
        self, transformer, mock_context
    ):
        """Multi-component compounds do not get an implicit parent structure."""
        record = {
            "molecule_id": 12345,
            "canonical_smiles": "CCO.Cl",
            "covalent_unit_count": 2,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["structure_parent_key"] is None
        assert result["chemical_standardization_status"] == "partial"
        assert json.loads(result["chemical_standardization_warnings"]) == [
            "multi_component_parent_deferred",
            "structure_parent_key_unavailable",
        ]

    @pytest.mark.asyncio
    async def test_compound_transformer__staged_finalization__555ae1dc(
        self, transformer, mock_context
    ):
        """Legacy PubChem transform should match staged finalization."""
        record = {
            "molecule_id": 2244,
            "molecular_formula": "C9H8O4",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "iupac_name": "  Aspirin  ",
        }

        pre_silver = await transformer.transform_pre_silver(
            mock_context, record, index=0
        )
        assert isinstance(pre_silver, PreSilverRecord)
        staged_result = RecordNormalizationProcessor(
            provider=transformer.provider,
        ).finalize_pre_silver(pre_silver, mock_context, 0)
        legacy_result = await transformer.transform(mock_context, record, index=0)

        assert staged_result is not None
        assert legacy_result is not None
        assert legacy_result["molecule_id"] == staged_result["molecule_id"]
        assert legacy_result["canonical_smiles"] == staged_result["canonical_smiles"]
        assert legacy_result["iupac_name"] == staged_result["iupac_name"]
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]

    @pytest.mark.asyncio
    async def test_compound_transformer__custom_provider__95eb10d6(self, mock_context):
        """Test transformation with custom provider."""
        transformer = instantiate_test_transformer(
            PubChemCompoundTransformer,
            provider="custom_pubchem",
        )
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "custom_pubchem" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_empty_molecule_id_returns_none(
        self, transformer, mock_context
    ):
        """Empty molecule_id should return None with warning logged."""
        record = {
            "molecule_id": "",
            "canonical_smiles": "C",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None
        mock_context.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_compound_transformer__fields_present__8b840789(self, transformer, mock_context):
        """Test that lineage fields are properly added to the result."""
        record = {
            "molecule_id": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Lineage fields should be present with underscore prefix
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert result["_source_batch_id"] is None
        assert "_ingestion_ts" in result
        # Verify types
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_float_conversion(
        self, transformer, mock_context
    ):
        """Test that molecular_weight is converted from string to float."""
        record = {
            "molecule_id": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.156",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecular_weight"] == pytest.approx(180.156)
        assert isinstance(result["molecular_weight"], float)

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_numeric_input(
        self, transformer, mock_context
    ):
        """Test that numeric molecular_weight is preserved as float."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": 180.156,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecular_weight"] == pytest.approx(180.156)
        assert isinstance(result["molecular_weight"], float)

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_none(self, transformer, mock_context):
        """Test that None molecular_weight is preserved as None."""
        record = {
            "molecule_id": 2244,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            # molecular_weight not provided
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_empty_string(
        self, transformer, mock_context
    ):
        """Test that empty string molecular_weight becomes None."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": "",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_invalid_string(
        self, transformer, mock_context
    ):
        """Test that invalid string molecular_weight becomes None."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": "invalid",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_negative(self, transformer, mock_context):
        """Test that negative molecular_weight becomes None."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": "-5.0",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("molecular_weight") is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_zero(self, transformer, mock_context):
        """Test that zero molecular_weight returns None (invalid: must be > 0)."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": "0",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Zero MW is invalid per validate_molecular_weight (range: 0 < mw < 100000)
        assert result["molecular_weight"] is None

    @pytest.mark.asyncio
    async def test_transform_molecular_weight_precision(
        self, transformer, mock_context
    ):
        """Test that molecular_weight precision is preserved up to 10 decimal places."""
        record = {
            "molecule_id": 2244,
            "molecular_weight": "1234.5678901234",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Should be rounded to 10 decimal places
        assert result["molecular_weight"] == pytest.approx(1234.5678901234, abs=1e-10)

    @pytest.mark.asyncio
    async def test_transform_all_physicochemical_properties(
        self, transformer, mock_context
    ):
        """Test transformation of record with all physicochemical properties.

        Verifies extraction of all fields defined in PubchemMoleculeSchema:
        - Structural identifiers
        - Physical properties (molecular_weight, exact_mass)
        - Computed descriptors (xlogp, tpsa, complexity, charge)
        - Atom/Bond counts
        - Stereochemistry counts
        - 3D properties
        """
        record = {
            # Primary key
            "molecule_id": 2244,
            # Structural identifiers
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            # Nomenclature
            "molecular_formula": "C9H8O4",
            "iupac_name": "2-acetoxybenzoic amolecule_id",
            # Physical properties
            "molecular_weight": 180.16,
            "exact_mass": 180.042259,
            "monoisotopic_mass": 180.042259,
            # Computed descriptors
            "xlogp": 1.2,
            "tpsa": 63.6,
            "complexity": 212.0,
            "charge": 0,
            # Atom/Bond counts
            "heavy_atom_count": 13,
            "h_bond_donor_count": 1,
            "h_bond_acceptor_count": 4,
            "rotatable_bond_count": 3,
            # Stereochemistry
            "atom_stereo_count": 0,
            "defined_atom_stereo_count": 0,
            "undefined_atom_stereo_count": 0,
            "bond_stereo_count": 0,
            "defined_bond_stereo_count": 0,
            "undefined_bond_stereo_count": 0,
            "isotope_atom_count": 0,
            "covalent_unit_count": 1,
            # 3D properties
            "volume_3d": 158.5,
            "conformer_count_3d": 1,
            "feature_acceptor_count_3d": 3,
            "feature_donor_count_3d": 1,
            "feature_anion_count_3d": 1,
            "feature_cation_count_3d": 0,
            "feature_ring_count_3d": 1,
            "feature_hydrophobe_count_3d": 1,
            "effective_rotor_count_3d": 2.4,
            "conformer_rmsd_3d": 0.4,
            # 3D steric quadrupole moments (can be negative)
            "x_steric_quadrupole_3d": 1.23,
            "y_steric_quadrupole_3d": -0.45,
            "z_steric_quadrupole_3d": 0.78,
            "feature_count_3d": 7,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Primary key
        assert result["molecule_id"] == "2244"
        # Structural identifiers
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["isomeric_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["inchi"].startswith("InChI=")
        assert result["inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        # Nomenclature
        assert result["molecular_formula"] == "C9H8O4"
        assert result["iupac_name"] == "2-acetoxybenzoic amolecule_id"
        # Physical properties
        assert result["molecular_weight"] == pytest.approx(180.16)
        assert result["exact_mass"] == pytest.approx(180.042259)
        assert result["monoisotopic_mass"] == pytest.approx(180.042259)
        # Computed descriptors
        assert result["xlogp"] == pytest.approx(1.2)
        assert result["tpsa"] == pytest.approx(63.6)
        assert result["complexity"] == pytest.approx(212.0)
        assert result["charge"] == 0
        # Atom/Bond counts
        assert result["heavy_atom_count"] == 13
        assert result["h_bond_donor_count"] == 1
        assert result["h_bond_acceptor_count"] == 4
        assert result["rotatable_bond_count"] == 3
        # Stereochemistry
        assert result["atom_stereo_count"] == 0
        assert result["defined_atom_stereo_count"] == 0
        assert result["undefined_atom_stereo_count"] == 0
        assert result["bond_stereo_count"] == 0
        assert result["defined_bond_stereo_count"] == 0
        assert result["undefined_bond_stereo_count"] == 0
        assert result["isotope_atom_count"] == 0
        assert result["covalent_unit_count"] == 1
        # 3D properties
        assert result["volume_3d"] == pytest.approx(158.5)
        assert result["conformer_count_3d"] == 1
        assert result["feature_acceptor_count_3d"] == 3
        assert result["feature_donor_count_3d"] == 1
        assert result["feature_anion_count_3d"] == 1
        assert result["feature_cation_count_3d"] == 0
        assert result["feature_ring_count_3d"] == 1
        assert result["feature_hydrophobe_count_3d"] == 1
        assert result["effective_rotor_count_3d"] == pytest.approx(2.4)
        assert result["conformer_rmsd_3d"] == pytest.approx(0.4)
        # 3D steric quadrupole moments
        assert result["x_steric_quadrupole_3d"] == pytest.approx(1.23)
        assert result["y_steric_quadrupole_3d"] == pytest.approx(-0.45)
        assert result["z_steric_quadrupole_3d"] == pytest.approx(0.78)
        assert result["feature_count_3d"] == 7

    @pytest.mark.asyncio
    async def test_transform_xlogp_negative_value(self, transformer, mock_context):
        """Test that negative XLogP values are preserved (valid range: -20 to 20)."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "xlogp": -5.2,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["xlogp"] == pytest.approx(-5.2)

    @pytest.mark.asyncio
    async def test_transform_charge_negative_value(self, transformer, mock_context):
        """Test that negative formal charge values are preserved."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "charge": -2,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["charge"] == -2

    @pytest.mark.asyncio
    async def test_transform_steric_quadrupole_negative_values(
        self, transformer, mock_context
    ):
        """Test that negative steric quadrupole values are preserved (can be negative)."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "x_steric_quadrupole_3d": -2.5,
            "y_steric_quadrupole_3d": -1.8,
            "z_steric_quadrupole_3d": -0.3,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["x_steric_quadrupole_3d"] == pytest.approx(-2.5)
        assert result["y_steric_quadrupole_3d"] == pytest.approx(-1.8)
        assert result["z_steric_quadrupole_3d"] == pytest.approx(-0.3)

    @pytest.mark.asyncio
    async def test_transform_monoisotopic_mass(self, transformer, mock_context):
        """Test that monoisotopic mass is validated as non-negative float."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "monoisotopic_mass": "16.031",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["monoisotopic_mass"] == pytest.approx(16.031)

    @pytest.mark.asyncio
    async def test_transform_monoisotopic_mass_negative_rejected(
        self, transformer, mock_context
    ):
        """Test that negative monoisotopic mass becomes None."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "monoisotopic_mass": -100.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("monoisotopic_mass") is None

    @pytest.mark.asyncio
    async def test_transform_feature_count_3d(self, transformer, mock_context):
        """Test that feature_count_3d is validated as non-negative integer."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "feature_count_3d": 10,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["feature_count_3d"] == 10

    @pytest.mark.asyncio
    async def test_transform_tpsa_invalid_negative(self, transformer, mock_context):
        """Test that negative TPSA values become None (must be >= 0)."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "tpsa": -10.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("tpsa") is None

    @pytest.mark.asyncio
    async def test_transform_complexity_invalid_negative(
        self, transformer, mock_context
    ):
        """Test that negative complexity values become None (must be >= 0)."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "complexity": -50.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("complexity") is None

    @pytest.mark.asyncio
    async def test_transform_atom_counts_string_conversion(
        self, transformer, mock_context
    ):
        """Test that string atom counts are converted to integers."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "heavy_atom_count": "5",
            "h_bond_donor_count": "2",
            "h_bond_acceptor_count": "3",
            "rotatable_bond_count": "1",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["heavy_atom_count"] == 5
        assert result["h_bond_donor_count"] == 2
        assert result["h_bond_acceptor_count"] == 3
        assert result["rotatable_bond_count"] == 1

    @pytest.mark.asyncio
    async def test_transform_3d_properties_optional(self, transformer, mock_context):
        """Test that 3D properties are optional and can be None."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            # No 3D properties provided
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("volume_3d") is None
        assert result.get("conformer_count_3d") is None
        assert result.get("feature_acceptor_count_3d") is None
        assert result.get("effective_rotor_count_3d") is None
        assert result.get("conformer_rmsd_3d") is None

    @pytest.mark.asyncio
    async def test_transform_stereo_counts_all_zero(self, transformer, mock_context):
        """Test transformation with zero stereochemistry counts (achiral molecule)."""
        record = {
            "molecule_id": 702,  # Ethanol
            "canonical_smiles": "CCO",
            "atom_stereo_count": 0,
            "defined_atom_stereo_count": 0,
            "undefined_atom_stereo_count": 0,
            "bond_stereo_count": 0,
            "defined_bond_stereo_count": 0,
            "undefined_bond_stereo_count": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["atom_stereo_count"] == 0
        assert result["defined_atom_stereo_count"] == 0
        assert result["undefined_atom_stereo_count"] == 0
        assert result["bond_stereo_count"] == 0
        assert result["defined_bond_stereo_count"] == 0
        assert result["undefined_bond_stereo_count"] == 0

    @pytest.mark.asyncio
    async def test_transform_stereo_counts_chiral_molecule(
        self, transformer, mock_context
    ):
        """Test transformation with non-zero stereochemistry counts (chiral molecule)."""
        record = {
            "molecule_id": 1,
            "canonical_smiles": "C[C@H](O)CC",
            "atom_stereo_count": 1,
            "defined_atom_stereo_count": 1,
            "undefined_atom_stereo_count": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["atom_stereo_count"] == 1
        assert result["defined_atom_stereo_count"] == 1
        assert result["undefined_atom_stereo_count"] == 0

    @pytest.mark.asyncio
    async def test_transform_covalent_unit_count(self, transformer, mock_context):
        """Test transformation with covalent_unit_count (>1 for salts/mixtures)."""
        record = {
            "molecule_id": 1,
            "canonical_smiles": "[Na+].[Cl-]",  # NaCl
            "covalent_unit_count": 2,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["covalent_unit_count"] == 2

    @pytest.mark.asyncio
    async def test_transform_exact_mass_validation(self, transformer, mock_context):
        """Test that exact_mass is validated as non-negative float."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "exact_mass": "16.031",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["exact_mass"] == pytest.approx(16.031)

    @pytest.mark.asyncio
    async def test_transform_exact_mass_negative_rejected(
        self, transformer, mock_context
    ):
        """Test that negative exact_mass becomes None."""
        record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "exact_mass": -100.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result.get("exact_mass") is None

    @pytest.mark.asyncio
    async def test_transform_content_hash_includes_all_properties(
        self, transformer, mock_context
    ):
        """Test that content_hash changes when physicochemical properties change."""
        base_record = {
            "molecule_id": 123,
            "canonical_smiles": "C",
        }

        record_with_xlogp = {
            "molecule_id": 123,
            "canonical_smiles": "C",
            "xlogp": 1.5,
        }

        result1 = await transformer.transform(mock_context, base_record, index=0)
        result2 = await transformer.transform(mock_context, record_with_xlogp, index=0)

        assert result1 is not None
        assert result2 is not None
        # Content hashes should differ because xlogp was added
        assert result1["content_hash"] != result2["content_hash"]


@pytest.mark.unit
class TestSafeFloatConversion:
    """Tests for safe_float conversion function."""

    @pytest.mark.parametrize(
        "input_mw,expected",
        [
            ("180.156", 180.156),
            ("0", 0.0),
            ("1234.5678901234", 1234.5678901234),
            ("", None),
            (None, None),
            ("invalid", None),
            ("-5.0", -5.0),  # safe_float converts, transformer filters negative
            (180.156, 180.156),
            (0, 0.0),
        ],
    )
    def test_molecular_weight_conversion(self, input_mw, expected):
        """Test safe_float conversion for molecular weight values."""
        result = safe_float(input_mw)
        if expected is None:
            assert result is None
        else:
            assert abs(result - expected) < 1e-10
