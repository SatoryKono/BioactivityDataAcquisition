"""Snapshot tests for transformers.

These tests capture the output of each transformer and compare against stored snapshots.
This helps detect unintended regressions in transformation logic.

Run with: pytest tests/unit/application/pipelines/test_transformer_snapshots.py -v
Update snapshots: pytest tests/unit/application/pipelines/test_transformer_snapshots.py --snapshot-update
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context with deterministic values."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()

    # Use a deterministic run_id for snapshot reproducibility
    run_id = uuid4()
    return PipelineContext(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


def normalize_for_snapshot(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize result for snapshot comparison.

    Removes dynamic fields that change between runs:
    - entity_id (contains hash)
    - content_hash (contains hash)
    - _run_id (UUID)
    - _ingestion_ts (timestamp)
    """
    if result is None:
        return None

    normalized = result.copy()

    # Replace dynamic fields with placeholders
    if "entity_id" in normalized:
        normalized["entity_id"] = "<entity_id>"
    if "content_hash" in normalized:
        normalized["content_hash"] = "<content_hash>"
    if "_run_id" in normalized:
        normalized["_run_id"] = "<run_id>"
    if "_ingestion_ts" in normalized:
        normalized["_ingestion_ts"] = "<ingestion_ts>"

    return normalized


@pytest.mark.unit
class TestActivityTransformerSnapshot:
    """Snapshot tests for ActivityTransformer."""

    @pytest.fixture
    def transformer(self) -> ActivityTransformer:
        return ActivityTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "activity_id": 12345678,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1862",
            "assay_chembl_id": "CHEMBL123456",
            "document_chembl_id": "CHEMBL789012",
            "record_id": 1234,
            "src_id": 1,
            "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
            "molecule_pref_name": "ASPIRIN",
            "target_pref_name": "Cyclooxygenase-2",
            "target_organism": "Homo sapiens",
            "assay_type": "B",
            "assay_description": "Binding assay",
            "standard_type": "IC50",
            "standard_value": 15.0,
            "standard_units": "nM",
            "standard_relation": "=",
            "pchembl_value": 7.82,
            "ligand_efficiency": {
                "bei": "14.06",
                "le": "0.26",
                "lle": "1.30",
                "sei": "5.56",
            },
            "document_year": 2024,
            "activity_comment": "High activity",
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: ActivityTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test ActivityTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestAssayTransformerSnapshot:
    """Snapshot tests for AssayTransformer."""

    @pytest.fixture
    def transformer(self) -> AssayTransformer:
        return AssayTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "assay_chembl_id": "CHEMBL1234567",
            "target_chembl_id": "CHEMBL123",
            "document_chembl_id": "CHEMBL456",
            "assay_type": "B",
            "assay_type_description": "Binding",
            "assay_organism": "Homo sapiens",
            "assay_tax_id": 9606,
            "description": "Test assay description",
            "confidence_score": 9,
            "bao_format": "BAO_0000357",
            "bao_label": "single protein format",
            "assay_classifications": [{"class": "Pharmacology"}],
            "assay_parameters": [{"param": "IC50"}],
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: AssayTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test AssayTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestDocumentTransformerSnapshot:
    """Snapshot tests for DocumentTransformer."""

    @pytest.fixture
    def transformer(self) -> DocumentTransformer:
        return DocumentTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "document_chembl_id": "CHEMBL1234567",
            "pubmed_id": 12345678,
            "doi": "10.1000/test.doi",
            "title": "Test Document Title",
            "authors": "Test Author, Another Author",
            "abstract": "This is a test abstract for the document.",
            "doc_type": "PUBLICATION",
            "journal": "Test Journal",
            "journal_full_title": "Full Test Journal Name",
            "year": 2024,
            "volume": "10",
            "issue": "5",
            "first_page": "100",
            "last_page": "110",
            "src_id": 1,
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: DocumentTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test DocumentTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestMoleculeTransformerSnapshot:
    """Snapshot tests for MoleculeTransformer."""

    @pytest.fixture
    def transformer(self) -> MoleculeTransformer:
        return MoleculeTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "molecule_chembl_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "molecule_type": "Small molecule",
            "structure_type": "MOL",
            "max_phase": 4,
            "first_approval": 1950,
            "oral": True,
            "black_box_warning": 0,
            "therapeutic_flag": True,
            "molecule_hierarchy": {
                "parent_chembl_id": "CHEMBL25",
                "active_chembl_id": "CHEMBL25",
                "molecule_chembl_id": "CHEMBL25",
            },
            "molecule_properties": {
                "alogp": 1.19,
                "mw_freebase": 180.16,
                "hba": 4,
                "hbd": 1,
                "psa": 63.6,
                "ro3_pass": "Y",
            },
            "molecule_structures": {
                "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "standard_inchi": "InChI=1S/C9H8O4/c...",
                "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            },
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: MoleculeTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test MoleculeTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestTargetTransformerSnapshot:
    """Snapshot tests for TargetTransformer."""

    @pytest.fixture
    def transformer(self) -> TargetTransformer:
        return TargetTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "target_chembl_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "tax_id": 9606,
            "description": "Prostaglandin G/H synthase 2",
            "target_components": [
                {
                    "accession": "P35354",
                    "component_id": 123,
                    "component_type": "PROTEIN",
                    "organism": "Homo sapiens",
                    "tax_id": 9606,
                    "target_component_xrefs": [
                        {"xref_id": "P35354", "xref_src_db": "UniProt"},
                    ],
                    "protein_classifications": [
                        {
                            "protein_classification_id": 597,
                            "pref_name": "Enzyme",
                            "short_name": "Oxidoreductase",
                        },
                    ],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: TargetTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test TargetTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestTargetComponentTransformerSnapshot:
    """Snapshot tests for TargetComponentTransformer."""

    @pytest.fixture
    def transformer(self) -> TargetComponentTransformer:
        return TargetComponentTransformer(provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "component_id": 123,
            "accession": "P12345",
            "component_type": "PROTEIN",
            "description": "Test protein component",
            "organism": "Homo sapiens",
            "tax_id": 9606,
            "target_component_synonyms": [{"synonym": "Gene1"}, {"synonym": "Protein1"}],
            "target_component_xrefs": [
                {"xref_id": "P12345", "xref_src_db": "UniProt"},
            ],
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: TargetComponentTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test TargetComponentTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestPubChemCompoundTransformerSnapshot:
    """Snapshot tests for PubChemCompoundTransformer."""

    @pytest.fixture
    def transformer(self) -> PubChemCompoundTransformer:
        return PubChemCompoundTransformer(provider="pubchem")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "cid": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.16",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c...",
            "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetyloxybenzoic acid",
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: PubChemCompoundTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test PubChemCompoundTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestUniProtProteinTransformerSnapshot:
    """Snapshot tests for UniProtProteinTransformer."""

    @pytest.fixture
    def transformer(self) -> UniProtProteinTransformer:
        return UniProtProteinTransformer(provider="uniprot")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Test protein"},
                },
            },
            "genes": [
                {"geneName": {"value": "TEST1"}},
                {"geneName": {"value": "TEST2"}},
            ],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 500},
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: UniProtProteinTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test UniProtProteinTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot
