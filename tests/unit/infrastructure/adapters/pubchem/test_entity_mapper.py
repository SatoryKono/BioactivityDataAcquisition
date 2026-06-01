"""Tests for PubChem entity mapper.

Covers PubChemEntityMapper static methods and private helpers:
- compound_to_dict, substance_to_dict, assay_to_dict
- _resolve_molecule_id, _extract_structural_fields, _extract_physicochemical_fields
- Edge cases: None values, missing attributes
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.entity_mapper import (
    PubChemEntityMapper,
    _extract_physicochemical_fields,
    _extract_structural_fields,
    _resolve_molecule_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def full_compound() -> MagicMock:
    """Compound mock with all attributes populated."""
    c = MagicMock()
    c.molecule_id = 2244
    c.cid = 2244
    c.connectivity_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    c.smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    c.inchi = "InChI=1S/C9H8O4/..."
    c.inchikey = "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
    c.molecular_formula = "C9H8O4"
    c.iupac_name = "2-acetyloxybenzoic acid"
    c.molecular_weight = 180.16
    c.exact_mass = 180.042259
    c.monoisotopic_mass = 180.042259
    c.xlogp = 1.2
    c.tpsa = 63.6
    c.complexity = 212
    c.charge = 0
    c.heavy_atom_count = 13
    c.h_bond_donor_count = 1
    c.h_bond_acceptor_count = 4
    c.rotatable_bond_count = 3
    # stereo
    c.atom_stereo_count = 0
    c.defined_atom_stereo_count = 0
    c.undefined_atom_stereo_count = 0
    c.bond_stereo_count = 0
    c.defined_bond_stereo_count = 0
    c.undefined_bond_stereo_count = 0
    c.isotope_atom_count = 0
    c.covalent_unit_count = 1
    # 3d
    c.volume_3d = 150.0
    c.conformer_count_3d = 1
    c.feature_acceptor_count_3d = 4
    c.feature_donor_count_3d = 1
    c.feature_anion_count_3d = 0
    c.feature_cation_count_3d = 0
    c.feature_ring_count_3d = 1
    c.feature_hydrophobe_count_3d = 0
    c.effective_rotor_count_3d = 3
    c.conformer_rmsd_3d = 0.5
    c.x_steric_quadrupole_3d = 1.23
    c.y_steric_quadrupole_3d = -0.45
    c.z_steric_quadrupole_3d = 0.78
    c.feature_count_3d = 7
    c.fingerprint = "mock_fp"
    return c


@pytest.fixture
def minimal_compound() -> MagicMock:
    """Compound mock with most attributes missing (uses spec to block getattr)."""
    c = MagicMock(spec=[])  # empty spec => getattr returns default via fallback
    c.cid = 999
    return c


@pytest.fixture
def full_substance() -> MagicMock:
    s = MagicMock()
    s.sid = 456
    s.source_name = "ChEMBL"
    s.source_id = "SRC-001"
    s.standardized_cids = [100, 200]
    s.synonyms = ["aspirin", "ASA"]
    return s


# ---------------------------------------------------------------------------
# _resolve_molecule_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveMoleculeId:
    """Tests for _resolve_molecule_id helper."""

    def test_returns_molecule_id_when_present(self, full_compound: MagicMock) -> None:
        assert _resolve_molecule_id(full_compound) == 2244

    def test_falls_back_to_cid_when_molecule_id_none(self) -> None:
        c = MagicMock(spec=[])
        c.cid = 777
        result = _resolve_molecule_id(c)
        assert result == 777

    def test_returns_none_when_both_missing(self) -> None:
        c = MagicMock(spec=[])
        result = _resolve_molecule_id(c)
        assert result is None

    def test_molecule_id_string_accepted(self) -> None:
        c = MagicMock(spec=[])
        c.molecule_id = "CHEMBL25"
        result = _resolve_molecule_id(c)
        assert result == "CHEMBL25"

    def test_molecule_id_non_scalar_ignored(self) -> None:
        """Non-str/int/float molecule_id should fall back to cid."""
        c = MagicMock(spec=[])
        c.molecule_id = [1, 2, 3]  # list is not str/int/float
        c.cid = 42
        result = _resolve_molecule_id(c)
        assert result == 42


# ---------------------------------------------------------------------------
# _extract_structural_fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractStructuralFields:
    def test_all_fields_present(self, full_compound: MagicMock) -> None:
        result = _extract_structural_fields(full_compound)
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["isomeric_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["inchi"] == "InChI=1S/C9H8O4/..."
        assert result["inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert result["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_missing_attrs_return_none(self) -> None:
        c = MagicMock(spec=[])
        result = _extract_structural_fields(c)
        for key in (
            "canonical_smiles",
            "isomeric_smiles",
            "inchi",
            "inchi_key",
            "inchikey",
        ):
            assert result[key] is None


# ---------------------------------------------------------------------------
# _extract_physicochemical_fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractPhysicochemicalFields:
    def test_physicochemical_fields__all_fields_present__337cac23(self, full_compound: MagicMock) -> None:
        result = _extract_physicochemical_fields(full_compound)
        assert result["molecular_formula"] == "C9H8O4"
        assert result["molecular_weight"] == pytest.approx(180.16)
        assert result["xlogp"] == pytest.approx(1.2)
        assert result["tpsa"] == pytest.approx(63.6)
        assert result["charge"] == 0
        assert result["h_bond_donor_count"] == 1

    def test_physicochemical_fields__attrs_return_none__15c6a8cf(self) -> None:
        c = MagicMock(spec=[])
        result = _extract_physicochemical_fields(c)
        assert result["molecular_formula"] is None
        assert result["molecular_weight"] is None


# ---------------------------------------------------------------------------
# PubChemEntityMapper.compound_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompoundToDict:
    def test_full_compound(self, full_compound: MagicMock) -> None:
        result = PubChemEntityMapper.compound_to_dict(full_compound)
        assert result["molecule_id"] == 2244
        assert result["cid"] == 2244
        assert result["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert result["molecular_formula"] == "C9H8O4"
        assert result["fingerprint"] == "mock_fp"

    def test_compound_with_missing_molecule_id_uses_cid(self) -> None:
        c = MagicMock(spec=[])
        c.cid = 999
        result = PubChemEntityMapper.compound_to_dict(c)
        assert result["molecule_id"] == 999
        assert result["cid"] == 999

    def test_compound_all_none(self) -> None:
        """Compound with no attributes produces dict with None values."""
        c = MagicMock(spec=[])
        result = PubChemEntityMapper.compound_to_dict(c)
        assert result["molecule_id"] is None
        assert result["cid"] is None
        assert result["canonical_smiles"] is None


# ---------------------------------------------------------------------------
# PubChemEntityMapper.substance_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSubstanceToDict:
    def test_full_substance(self, full_substance: MagicMock) -> None:
        result = PubChemEntityMapper.substance_to_dict(full_substance)
        assert result["sid"] == 456
        assert result["source_name"] == "ChEMBL"
        assert result["source_id"] == "SRC-001"
        assert result["cids"] == [100, 200]
        assert result["synonyms"] == ["aspirin", "ASA"]

    def test_substance_empty_synonyms(self) -> None:
        s = MagicMock()
        s.sid = 1
        s.source_name = "Test"
        s.source_id = "T1"
        s.standardized_cids = []
        s.synonyms = []
        result = PubChemEntityMapper.substance_to_dict(s)
        assert result["synonyms"] == []
        assert result["cids"] == []


# ---------------------------------------------------------------------------
# PubChemEntityMapper.assay_to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAssayToDict:
    def test_dict_input(self) -> None:
        data = {
            "aid": 789,
            "name": "Binding Assay",
            "description": "IC50",
            "protocol": "HTS",
            "target": "EGFR",
        }
        result = PubChemEntityMapper.assay_to_dict(data)
        assert result["aid"] == 789
        assert result["name"] == "Binding Assay"
        assert result["target"] == "EGFR"

    def test_dict_input_missing_keys(self) -> None:
        result = PubChemEntityMapper.assay_to_dict({})
        assert result["aid"] is None
        assert result["name"] is None

    def test_object_input(self) -> None:
        obj = MagicMock()
        obj.aid = 100
        obj.name = "Obj Assay"
        obj.description = "Desc"
        obj.protocol = "Proto"
        obj.target = "Target"
        result = PubChemEntityMapper.assay_to_dict(obj)
        assert result["aid"] == 100
        assert result["name"] == "Obj Assay"

    def test_object_input_missing_attrs(self) -> None:
        obj = MagicMock(spec=[])
        result = PubChemEntityMapper.assay_to_dict(obj)
        assert result["aid"] is None
        assert result["name"] is None
