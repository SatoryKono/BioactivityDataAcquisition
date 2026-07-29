# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for PubChem domain entity — PubchemMolecule."""

from __future__ import annotations

from typing import Any, cast


from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.pubchem import PubchemMolecule

BASE_KWARGS = cast(
    Any,
    {
        "entity_id": "pubchem:2244",
        "content_hash": "hash123",
        "run_id": "run-001",
        "run_type": "incremental",
        "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
        "_index": 0,
    },
)


@pytest.mark.unit
class TestPubchemMolecule:
    """Tests for PubchemMolecule domain entity."""

    def test_valid_creation_with_smiles(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        assert m.molecule_id == "2244"
        assert m.canonical_smiles == "CC(=O)OC1=CC=CC=C1C(=O)O"

    def test_valid_creation_with_inchi(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            inchi="InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
        )
        assert m.inchi is not None

    def test_valid_creation_with_isomeric_smiles(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            isomeric_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        assert m.isomeric_smiles is not None

    def test_pubchem_molecule__molecule_id_raises__fc40f478(self) -> None:
        with pytest.raises(ValueError, match="molecule_id is required"):
            PubchemMolecule(
                **BASE_KWARGS,
                molecule_id="",
                canonical_smiles="C",
            )

    def test_no_structural_identifier_raises(self) -> None:
        with pytest.raises(ValueError, match="structural identifier"):
            PubchemMolecule(
                **BASE_KWARGS,
                molecule_id="2244",
            )

    def test_inchi_key_alone_not_sufficient(self) -> None:
        with pytest.raises(ValueError, match="structural identifier"):
            PubchemMolecule(
                **BASE_KWARGS,
                molecule_id="2244",
                inchi_key="BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            )

    def test_pubchem_molecule__with_properties__39fdf423(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            canonical_smiles="C",
            molecular_formula="C9H8O4",
            molecular_weight=180.16,
            xlogp=1.2,
            tpsa=63.6,
            heavy_atom_count=13,
            h_bond_donor_count=1,
            h_bond_acceptor_count=4,
            rotatable_bond_count=3,
        )
        assert m.molecular_weight == pytest.approx(180.16)
        assert m.h_bond_donor_count == 1

    def test_valid_creation_with_3d_properties(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            canonical_smiles="C",
            volume_3d=150.5,
            conformer_count_3d=1,
            feature_acceptor_count_3d=2,
        )
        assert m.volume_3d == pytest.approx(150.5)

    def test_pubchem_molecule__immutable__9c58717b(self) -> None:
        m = PubchemMolecule(
            **BASE_KWARGS,
            molecule_id="2244",
            canonical_smiles="C",
        )
        with pytest.raises((AttributeError, TypeError)):
            m.molecule_id = "other"  # type: ignore[misc]
