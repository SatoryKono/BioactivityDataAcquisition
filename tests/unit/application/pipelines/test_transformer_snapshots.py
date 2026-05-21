"""Snapshot tests for transformers.

These tests capture the output of each transformer and compare against stored snapshots.
This helps detect unintended regressions in transformation logic.

Run with: pytest tests/unit/application/pipelines/test_transformer_snapshots.py -v
Update snapshots: pytest tests/unit/application/pipelines/test_transformer_snapshots.py --snapshot-update

Requires: pip install syrupy
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Skip entire module if syrupy is not installed
pytest.importorskip("syrupy", reason="syrupy package required for snapshot tests")
pytestmark = pytest.mark.repo_backed

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import (
    build_test_transformer_dependencies,
    instantiate_test_transformer,
)


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context with deterministic values."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()

    # run_id is randomized; normalize_for_snapshot replaces it with placeholder
    run_id = uuid4()
    return PipelineContext(
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture(scope="module", autouse=True)
def initialize_publication_classification() -> None:
    """Bootstrap publication-type classification for publication transformers."""
    repo_root = Path(__file__).resolve().parents[4]
    initialize_publication_type_classification(repo_root / "configs")


def normalize_for_snapshot(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize result for snapshot comparison.

    Removes dynamic fields that change between runs:
    - entity_id (contains hash)
    - content_hash (contains hash)
    - runtime provenance/meta fields that are validated elsewhere and should
      not cause snapshot churn
    """
    if result is None:
        return None

    normalized = result.copy()

    # Replace dynamic fields with placeholders
    if "entity_id" in normalized:
        normalized["entity_id"] = "<entity_id>"
    if "content_hash" in normalized:
        normalized["content_hash"] = "<content_hash>"

    # Runtime provenance is asserted by dedicated contract tests, not snapshots.
    normalized.pop("_run_id", None)
    normalized.pop("_run_type", None)
    normalized.pop("_source_batch_id", None)
    normalized.pop("_ingestion_ts", None)

    return normalized


@pytest.mark.unit
class TestActivityTransformerSnapshot:
    """Snapshot tests for ActivityTransformer."""

    @pytest.fixture
    def transformer(self) -> ActivityTransformer:
        return instantiate_test_transformer(ActivityTransformer, provider="chembl")

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "activity_id": 12345678,
            "molecule_id": "CHEMBL25",
            "target_id": "CHEMBL1862",
            "assay_id": "CHEMBL123456",
            "publication_id": "CHEMBL789012",
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
            "publication_year": 2024,
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestAssayTransformerSnapshot:
    """Snapshot tests for AssayTransformer."""

    @pytest.fixture
    def transformer(self) -> AssayTransformer:
        return AssayTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "assay_id": "CHEMBL1234567",
            "target_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "src_id": 1,
            "assay_type": "B",
            "assay_type_description": "Binding",
            "assay_organism": "Homo sapiens",
            "assay_tax_id": 9606,  # Source API field name
            "description": "Test assay description",
            "confidence_score": 9,
            "relationship_type": "D",
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestPublicationTransformerSnapshot:
    """Snapshot tests for PublicationTransformer."""

    @pytest.fixture
    def transformer(self) -> PublicationTransformer:
        return PublicationTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "publication_id": "CHEMBL1234567",
            "pubmed_id": "12345678",  # Source API field name
            "doi": "10.1000/test.doi",
            "title": "Test Document Title",
            "authors": "Test Author, Another Author",
            "abstract": "This is a test abstract for the document.",
            "doc_type": "PUBLICATION",
            "journal": "Test Journal",
            "year": 2024,
            "volume": "10",
            "issue": "5",
            "first_page": "100",
            "last_page": "110",
            "src_id": 1,
            # ChEMBL release metadata
            "chembl_release": {
                "chembl_release": "CHEMBL_34",
                "creation_date": "2024-01-15",
            },
        }

    @pytest.mark.asyncio
    async def test_transform_snapshot(
        self,
        transformer: PublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test PublicationTransformer output matches snapshot."""
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestMoleculeTransformerSnapshot:
    """Snapshot tests for MoleculeTransformer."""

    @pytest.fixture
    def transformer(self) -> MoleculeTransformer:
        return MoleculeTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "molecule_id": "CHEMBL25",
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
                "molecule_id": "CHEMBL25",
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestTargetTransformerSnapshot:
    """Snapshot tests for TargetTransformer."""

    @pytest.fixture
    def transformer(self) -> TargetTransformer:
        return TargetTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        # Note: protein_classifications are NOT available in /target endpoint.
        # They are only available via /target_component endpoint.
        return {
            "target_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "tax_id": 9606,  # Source API field name
            "description": "Prostaglandin G/H synthase 2",
            "target_components": [
                {
                    "accession": "P35354",
                    "component_id": 123,
                    "component_type": "PROTEIN",
                    "organism": "Homo sapiens",
                    "tax_id": 9606,  # Source API field name
                    "target_component_xrefs": [
                        {"xref_id": "P35354", "xref_src_db": "UniProt"},
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestTargetComponentTransformerSnapshot:
    """Snapshot tests for TargetComponentTransformer."""

    @pytest.fixture
    def transformer(self) -> TargetComponentTransformer:
        return TargetComponentTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "component_id": 123,
            "accession": "P12345",
            "component_type": "PROTEIN",
            "description": "Test protein component",
            "organism": "Homo sapiens",
            "tax_id": 9606,  # Source API field name
            "target_component_synonyms": [
                {"synonym": "Gene1"},
                {"synonym": "Protein1"},
            ],
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestPubChemCompoundTransformerSnapshot:
    """Snapshot tests for PubChemCompoundTransformer."""

    @pytest.fixture
    def transformer(self) -> PubChemCompoundTransformer:
        return instantiate_test_transformer(
            PubChemCompoundTransformer,
            provider="pubchem",
        )

    @pytest.fixture
    def sample_record(self) -> dict[str, Any]:
        return {
            "molecule_id": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": "180.16",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c...",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetyloxybenzoic amolecule_id",
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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


@pytest.mark.unit
class TestUniProtProteinTransformerSnapshot:
    """Snapshot tests for UniProtProteinTransformer."""

    @pytest.fixture
    def transformer(self) -> UniProtProteinTransformer:
        return instantiate_test_transformer(
            UniProtProteinTransformer,
            provider="uniprot",
        )

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
        result = await transformer.transform(mock_context, sample_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot


# Sample PubMed XML for snapshot tests
PUBMED_MINIMAL_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>12345678</PMID>
    <Article>
      <ArticleTitle>Test Article Title</ArticleTitle>
    </Article>
  </MedlineCitation>
</PubmedArticle>
"""

PUBMED_FULL_XML = """<?xml version="1.0"?>
<PubmedArticle>
  <MedlineCitation>
    <PMID>98765432</PMID>
    <Article>
      <Journal>
        <ISSN IssnType="Print">1234-5678</ISSN>
        <JournalIssue>
          <Volume>42</Volume>
          <Issue>3</Issue>
          <PubDate>
            <Year>2025</Year>
            <Month>Mar</Month>
            <Day>15</Day>
          </PubDate>
        </JournalIssue>
        <Title>Journal of Test Science</Title>
        <ISOAbbreviation>J Test Sci</ISOAbbreviation>
      </Journal>
      <ArticleTitle>A Comprehensive Study of Unit Testing</ArticleTitle>
      <Pagination>
        <MedlinePgn>123-145</MedlinePgn>
      </Pagination>
      <ELocationID EIdType="doi">10.1234/test.2025.001</ELocationID>
      <Abstract>
        <AbstractText>This is the abstract of the test article.</AbstractText>
      </Abstract>
      <AuthorList>
        <Author>
          <LastName>Smith</LastName>
          <ForeName>John</ForeName>
        </Author>
        <Author>
          <LastName>Doe</LastName>
          <ForeName>Jane</ForeName>
        </Author>
      </AuthorList>
      <Language>eng</Language>
      <PublicationTypeList>
        <PublicationType>Journal Article</PublicationType>
        <PublicationType>Research Support</PublicationType>
      </PublicationTypeList>
      <ArticleDate DateType="Electronic">
        <Year>2025</Year>
        <Month>02</Month>
        <Day>28</Day>
      </ArticleDate>
    </Article>
    <MedlineJournalInfo>
      <Country>United States</Country>
    </MedlineJournalInfo>
    <KeywordList>
      <Keyword>unit testing</Keyword>
      <Keyword>python</Keyword>
    </KeywordList>
    <MeshHeadingList>
      <MeshHeading>
        <DescriptorName>Software Testing</DescriptorName>
      </MeshHeading>
    </MeshHeadingList>
  </MedlineCitation>
  <PubmedData>
    <History>
      <PubMedPubDate PubStatus="received">
        <Year>2024</Year>
        <Month>12</Month>
        <Day>01</Day>
      </PubMedPubDate>
      <PubMedPubDate PubStatus="accepted">
        <Year>2025</Year>
        <Month>01</Month>
        <Day>15</Day>
      </PubMedPubDate>
      <PubMedPubDate PubStatus="revised">
        <Year>2025</Year>
        <Month>01</Month>
        <Day>10</Day>
      </PubMedPubDate>
    </History>
    <ArticleIdList>
      <ArticleId IdType="pubmed">98765432</ArticleId>
      <ArticleId IdType="pmc">PMC1234567</ArticleId>
    </ArticleIdList>
  </PubmedData>
</PubmedArticle>
"""


@pytest.mark.unit
class TestPubMedPublicationTransformerSnapshot:
    """Snapshot tests for PubMedPublicationTransformer."""

    @pytest.fixture
    def transformer(self) -> PubMedPublicationTransformer:
        return instantiate_test_transformer(
            PubMedPublicationTransformer,
            provider="pubmed",
        )

    @pytest.fixture
    def minimal_record(self) -> dict[str, Any]:
        """Minimal valid PubMed record."""
        return {"_raw_xml": PUBMED_MINIMAL_XML}

    @pytest.fixture
    def full_record(self) -> dict[str, Any]:
        """Full PubMed record with all fields."""
        return {"_raw_xml": PUBMED_FULL_XML}

    @pytest.mark.asyncio
    async def test_transform_minimal_snapshot(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
        minimal_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test PubMedPublicationTransformer minimal output matches snapshot."""
        result = await transformer.transform(mock_context, minimal_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot

    @pytest.mark.asyncio
    async def test_transform_full_snapshot(
        self,
        transformer: PubMedPublicationTransformer,
        mock_context: PipelineContext,
        full_record: dict[str, Any],
        snapshot: Any,
    ) -> None:
        """Test PubMedPublicationTransformer full output matches snapshot."""
        result = await transformer.transform(mock_context, full_record, index=0)
        normalized = normalize_for_snapshot(result)
        assert normalized == snapshot
