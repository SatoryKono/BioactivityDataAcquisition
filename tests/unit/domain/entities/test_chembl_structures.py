# pyright: reportArgumentType=false
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for ChEMBL structural entities — Target, Molecule, ChemblPublicationTerm, etc."""

from __future__ import annotations

from typing import Any, cast


from datetime import UTC, datetime

import pytest

BASE_KWARGS = cast(Any, {
    "entity_id": "chembl:test:001",
    "content_hash": "hash123",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    "_index": 0,
})


@pytest.mark.unit
class TestDocumentTerm:
    """Tests for ChemblPublicationTerm entity."""

    def test_document_term__valid_creation__77ef3848(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        dt = ChemblPublicationTerm(
            **BASE_KWARGS,
            publication_id="CHEMBL1125145",
            term="Aspirin",
            term_type="KEYWORD",
        )
        assert dt.term == "Aspirin"
        assert dt.term_type == "KEYWORD"
        assert dt.mesh_id is None

    def test_valid_mesh_heading(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        dt = ChemblPublicationTerm(
            **BASE_KWARGS,
            publication_id="CHEMBL1",
            term="Kinases",
            term_type="MESH_HEADING",
            mesh_id="D001241",
            qualifier="pharmacology",
        )
        assert dt.mesh_id == "D001241"
        assert dt.qualifier == "pharmacology"

    def test_document_term__id_raises__78eeb187(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        with pytest.raises(ValueError, match="Document ChEMBL ID is required"):
            ChemblPublicationTerm(
                **BASE_KWARGS,
                publication_id="",
                term="Test",
                term_type="KEYWORD",
            )

    def test_empty_term_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        with pytest.raises(ValueError, match="Term text is required"):
            ChemblPublicationTerm(
                **BASE_KWARGS,
                publication_id="CHEMBL1",
                term="",
                term_type="KEYWORD",
            )

    def test_empty_term_type_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        with pytest.raises(ValueError, match="Term type is required"):
            ChemblPublicationTerm(
                **BASE_KWARGS,
                publication_id="CHEMBL1",
                term="Test",
                term_type="",
            )

    def test_invalid_term_type_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        with pytest.raises(ValueError, match="term_type must be one of"):
            ChemblPublicationTerm(
                **BASE_KWARGS,
                publication_id="CHEMBL1",
                term="Test",
                term_type="INVALID",
            )

    @pytest.mark.parametrize(
        "valid_type",
        ["MESH_HEADING", "MESH_QUALIFIER", "KEYWORD"],
    )
    def test_valid_term_types(self, valid_type: str) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        dt = ChemblPublicationTerm(
            **BASE_KWARGS,
            publication_id="CHEMBL1",
            term="Test",
            term_type=valid_type,
        )
        assert dt.term_type == valid_type

    def test_document_term__immutable__9341f838(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationTerm

        dt = ChemblPublicationTerm(
            **BASE_KWARGS,
            publication_id="CHEMBL1",
            term="Test",
            term_type="KEYWORD",
        )
        with pytest.raises((AttributeError, TypeError)):
            dt.term = "Other"  # type: ignore[misc]


@pytest.mark.unit
class TestTarget:
    """Tests for Target entity."""

    def test_structures_target__creation_minimal__ec9ccc3f(self) -> None:
        from bioetl.domain.entities.chembl_structures import Target

        t = Target(**BASE_KWARGS, target_id="CHEMBL204")
        assert t.target_id == "CHEMBL204"
        assert t.pref_name is None
        assert t.target_type is None

    def test_structures_target__valid_creation_full__81316345(self) -> None:
        from bioetl.domain.entities.chembl_structures import Target

        t = Target(
            **BASE_KWARGS,
            target_id="CHEMBL204",
            pref_name="Thrombin",
            target_type="SINGLE PROTEIN",
            organism="Homo sapiens",
            taxonomy_id=9606,
            target_description="Serine protease target",
        )
        assert t.pref_name == "Thrombin"
        assert t.taxonomy_id == 9606
        assert t.target_description == "Serine protease target"

    def test_empty_target_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import Target

        with pytest.raises(ValueError, match="Target ChEMBL ID is required"):
            Target(**BASE_KWARGS, target_id="")


@pytest.mark.unit
class TestMolecule:
    """Tests for Molecule entity."""

    def test_structures_molecule__creation_minimal__72bce9ff(self) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        m = Molecule(**BASE_KWARGS, molecule_id="CHEMBL25")
        assert m.molecule_id == "CHEMBL25"
        assert m.max_phase is None
        assert m.logp is None

    def test_valid_creation_with_properties(self) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        m = Molecule(
            **BASE_KWARGS,
            molecule_id="CHEMBL25",
            pref_name="Aspirin",
            molecule_type="Small molecule",
            max_phase=4,
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            molecular_weight=180.16,
            logp=-0.03,
        )
        assert m.pref_name == "Aspirin"
        assert m.max_phase == 4
        assert m.molecular_weight == pytest.approx(180.16)

    def test_structures_molecule__molecule_id_raises__7915f8f8(self) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        with pytest.raises(ValueError, match="Molecule ChEMBL ID is required"):
            Molecule(**BASE_KWARGS, molecule_id="")

    def test_invalid_max_phase_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        with pytest.raises(ValueError, match="max_phase must be one of"):
            Molecule(**BASE_KWARGS, molecule_id="CHEMBL25", max_phase=5)

    @pytest.mark.parametrize("phase", [-1, 0, 0.5, 1, 2, 3, 4])
    def test_valid_max_phase(self, phase: int | float) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        m = Molecule(**BASE_KWARGS, molecule_id="CHEMBL25", max_phase=phase)
        assert m.max_phase == phase

    def test_max_phase_none_is_valid(self) -> None:
        from bioetl.domain.entities.chembl_structures import Molecule

        m = Molecule(**BASE_KWARGS, molecule_id="CHEMBL25", max_phase=None)
        assert m.max_phase is None


@pytest.mark.unit
class TestCellLine:
    """Tests for CellLine entity."""

    def test_structures_cell_line__valid_creation__fc9d06eb(self) -> None:
        from bioetl.domain.entities.chembl_structures import CellLine

        cl = CellLine(
            **BASE_KWARGS,
            cell_id="CHEMBL3308391",
            cell_name="HeLa",
        )
        assert cl.cell_id == "CHEMBL3308391"
        assert cl.cell_name == "HeLa"

    def test_structures_cell_line__valid_creation_full__0f12b21b(self) -> None:
        from bioetl.domain.entities.chembl_structures import CellLine

        cl = CellLine(
            **BASE_KWARGS,
            cell_id="CHEMBL3308391",
            cell_name="HeLa",
            cell_source_organism="Homo sapiens",
            cell_source_taxonomy_id=9606,
            cellosaurus_id="CVCL_0030",
        )
        assert cl.cell_source_taxonomy_id == 9606

    def test_empty_cell_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import CellLine

        with pytest.raises(ValueError, match="Cell ChEMBL ID is required"):
            CellLine(**BASE_KWARGS, cell_id="", cell_name="HeLa")

    def test_empty_cell_name_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import CellLine

        with pytest.raises(ValueError, match="Cell name is required"):
            CellLine(**BASE_KWARGS, cell_id="CHEMBL1", cell_name="")

    def test_invalid_taxonomy_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import CellLine

        with pytest.raises(ValueError, match="cell_source_taxonomy_id must be >= 1"):
            CellLine(
                **BASE_KWARGS,
                cell_id="CHEMBL1",
                cell_name="HeLa",
                cell_source_taxonomy_id=0,
            )


@pytest.mark.unit
class TestDocumentSimilarity:
    """Tests for ChemblPublicationSimilarity entity."""

    def test_document_similarity__valid_creation__30845894(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationSimilarity

        ds = ChemblPublicationSimilarity(
            **BASE_KWARGS,
            sim_id=1,
            doc_1=100,
            doc_2=200,
        )
        assert ds.sim_id == 1
        assert ds.doc_1 == 100

    def test_valid_with_tanimoto(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationSimilarity

        ds = ChemblPublicationSimilarity(
            **BASE_KWARGS,
            sim_id=1,
            doc_1=100,
            doc_2=200,
            tid_tani=0.75,
            mol_tani=0.80,
        )
        assert ds.tid_tani == pytest.approx(0.75)
        assert ds.mol_tani == pytest.approx(0.80)

    def test_zero_sim_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationSimilarity

        with pytest.raises(ValueError, match="sim_id must be positive"):
            ChemblPublicationSimilarity(**BASE_KWARGS, sim_id=0, doc_1=1, doc_2=2)

    def test_same_document_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationSimilarity

        with pytest.raises(ValueError, match="cannot be similar to itself"):
            ChemblPublicationSimilarity(**BASE_KWARGS, sim_id=1, doc_1=100, doc_2=100)

    def test_tanimoto_out_of_range_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ChemblPublicationSimilarity

        with pytest.raises(ValueError, match="must be in"):
            ChemblPublicationSimilarity(
                **BASE_KWARGS,
                sim_id=1,
                doc_1=100,
                doc_2=200,
                tid_tani=1.5,
            )


@pytest.mark.unit
class TestProteinClassification:
    """Tests for ProteinClassification entity."""

    def test_protein_classification__valid_creation__d53c3e72(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        pc = ProteinClassification(
            **BASE_KWARGS,
            protein_class_id=1,
        )
        assert pc.protein_class_id == 1
        assert pc.is_root() is True

    def test_valid_with_hierarchy(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        pc = ProteinClassification(
            **BASE_KWARGS,
            protein_class_id=5,
            parent_id=1,
            class_level=2,
            pref_name="Kinase",
        )
        assert pc.is_root() is False
        assert pc.class_level == 2

    def test_invalid_class_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        with pytest.raises(ValueError, match="protein_class_id must be >= 1"):
            ProteinClassification(**BASE_KWARGS, protein_class_id=0)

    def test_invalid_class_level_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        with pytest.raises(ValueError, match="class_level must be 1-8"):
            ProteinClassification(**BASE_KWARGS, protein_class_id=1, class_level=9)

    def test_deprecated_detection(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        pc = ProteinClassification(
            **BASE_KWARGS,
            protein_class_id=1,
            replaced_by=2,
        )
        assert pc.is_deprecated() is True

    def test_downgraded_detection(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        pc = ProteinClassification(
            **BASE_KWARGS,
            protein_class_id=1,
            downgraded=1,
        )
        assert pc.is_deprecated() is True

    def test_invalid_downgraded_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import ProteinClassification

        with pytest.raises(ValueError, match="downgraded must be 0 or 1"):
            ProteinClassification(**BASE_KWARGS, protein_class_id=1, downgraded=2)


@pytest.mark.unit
class TestTargetComponent:
    """Tests for TargetComponent entity."""

    def test_target_component__valid_creation__3361d517(self) -> None:
        from bioetl.domain.entities.chembl_structures import TargetComponent

        tc = TargetComponent(**BASE_KWARGS, component_id=12345)
        assert tc.component_id == 12345

    def test_falsy_component_id_raises(self) -> None:
        from bioetl.domain.entities.chembl_structures import TargetComponent

        with pytest.raises(ValueError, match="Component ID is required"):
            TargetComponent(**BASE_KWARGS, component_id=0)
