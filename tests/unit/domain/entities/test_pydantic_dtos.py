# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
# Entity fixture overrides use intentional wide test inputs (PD2-9).
"""Unit tests for Pydantic DTO models — frozen, extra=forbid."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestCrossRefPublicationRecord:
    """Tests for CrossRef PublicationRecord DTO."""

    def test_ref_publication_record__valid_creation__0c29ed22(self) -> None:
        from bioetl.domain.entities.crossref import PublicationRecord

        r = PublicationRecord(doi="10.1038/nature12373")
        assert r.doi == "10.1038/nature12373"
        assert r.title is None
        assert r.issn == []

    def test_ref_publication_record__field_forbidden__6ad22584(self) -> None:
        from bioetl.domain.entities.crossref import PublicationRecord

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PublicationRecord(doi="10.1234/test", unknown_field="x")  # type: ignore[call-arg]

    def test_ref_publication_record__frozen__fca41406(self) -> None:
        from bioetl.domain.entities.crossref import PublicationRecord

        r = PublicationRecord(doi="10.1234/test")
        with pytest.raises(ValidationError):
            r.doi = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestPubchemMoleculeRecord:
    """Tests for PubChem PubchemMoleculeRecord DTO."""

    def test_molecule_record__valid_creation__d3ebf740(self) -> None:
        from bioetl.domain.entities.pubchem import PubchemMoleculeRecord

        r = PubchemMoleculeRecord(molecule_id="2244")
        assert r.molecule_id == "2244"
        assert r.canonical_smiles is None

    def test_molecule_record__field_forbidden__7cbb50dd(self) -> None:
        from bioetl.domain.entities.pubchem import PubchemMoleculeRecord

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PubchemMoleculeRecord(molecule_id="2244", bad_field="x")  # type: ignore[call-arg]

    def test_molecule_record__frozen__f5dce46f(self) -> None:
        from bioetl.domain.entities.pubchem import PubchemMoleculeRecord

        r = PubchemMoleculeRecord(molecule_id="2244")
        with pytest.raises(ValidationError):
            r.molecule_id = "other"  # type: ignore[misc]

    def test_with_properties(self) -> None:
        from bioetl.domain.entities.pubchem import PubchemMoleculeRecord

        r = PubchemMoleculeRecord(
            molecule_id="2244",
            molecular_weight=180.16,
            canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
            xlogp=1.2,
        )
        assert r.molecular_weight == pytest.approx(180.16)


@pytest.mark.unit
class TestChEMBLRecordDTOs:
    """Tests for ChEMBL Pydantic DTO models."""

    def test_activity_record(self) -> None:
        from bioetl.domain.entities.chembl import ActivityRecord

        r = ActivityRecord(
            activity_id="12345",
            molecule_id="CHEMBL25",
        )
        assert r.activity_id == "12345"
        assert r.molecule_id == "CHEMBL25"

    def test_activity_record_extra_forbidden(self) -> None:
        from bioetl.domain.entities.chembl import ActivityRecord

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ActivityRecord(
                activity_id="1",
                molecule_id="CHEMBL1",
                nonexistent="x",  # type: ignore[call-arg]
            )

    def test_assay_record(self) -> None:
        from bioetl.domain.entities.chembl import AssayRecord

        r = AssayRecord(assay_id="CHEMBL1000")
        assert r.assay_id == "CHEMBL1000"
        assert r.confidence_score is None

    def test_molecule_record(self) -> None:
        from bioetl.domain.entities.chembl import MoleculeRecord

        r = MoleculeRecord(molecule_id="CHEMBL25")
        assert r.molecule_id == "CHEMBL25"
        assert r.max_phase is None

    def test_target_record(self) -> None:
        from bioetl.domain.entities.chembl import TargetRecord

        r = TargetRecord(target_id="CHEMBL204")
        assert r.target_id == "CHEMBL204"

    def test_cell_line_record(self) -> None:
        from bioetl.domain.entities.chembl import CellLineRecord

        r = CellLineRecord(cell_id="CHEMBL3308391", cell_name="HeLa")
        assert r.cell_id == "CHEMBL3308391"

    def test_protein_class_record(self) -> None:
        from bioetl.domain.entities.chembl import ProteinClassRecord

        r = ProteinClassRecord(protein_class_id=1)
        assert r.protein_class_id == 1
