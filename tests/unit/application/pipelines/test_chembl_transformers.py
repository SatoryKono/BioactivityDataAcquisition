"""Unit tests for ChEMBL transformers (Assay, Document, Molecule, Target)."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestAssayTransformer:
    """Tests for AssayTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create AssayTransformer instance."""
        return AssayTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid assay record."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "target_chembl_id": "CHEMBL123",
            "document_chembl_id": "CHEMBL456",
            "assay_type": "B",
            "assay_type_description": "Binding",
            "description": "Test assay description",
            "confidence_score": 9,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["assay_chembl_id"] == "CHEMBL1234567"
        assert result["target_chembl_id"] == "CHEMBL123"
        assert result["assay_type"] == "B"
        assert result["confidence_score"] == 9
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_assay_id(self, transformer, mock_context):
        """Test transformation returns None when assay_chembl_id is missing."""
        record = {
            "target_chembl_id": "CHEMBL123",
            "assay_type": "B",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_json_fields(self, transformer, mock_context):
        """Test transformation handles complex JSON fields."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "assay_classifications": [{"class": "Pharmacology"}],
            "assay_parameters": [{"param": "IC50"}],
            "variant_sequence": {"sequence": "ATCG"},
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # JSON fields should be serialized as strings
        assert isinstance(result.get("assay_classifications"), str)
        assert isinstance(result.get("assay_parameters"), str)

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = AssayTransformer(provider="custom_provider")
        record = {"assay_chembl_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert "entity_id" in result


@pytest.mark.unit
class TestDocumentTransformer:
    """Tests for DocumentTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create DocumentTransformer instance."""
        return DocumentTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid document record."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "pubmed_id": 12345678,
            "doi": "10.1000/test.doi",
            "title": "Test Document Title",
            "authors": "Test Author",
            "journal": "Test Journal",
            "year": 2024,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["document_chembl_id"] == "CHEMBL1234567"
        assert result["pubmed_id"] == 12345678
        assert result["doi"] == "10.1000/test.doi"
        assert result["year"] == 2024
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_document_id(self, transformer, mock_context):
        """Test transformation returns None when document_chembl_id is missing."""
        record = {
            "pubmed_id": 12345678,
            "title": "Test Document",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_all_fields(self, transformer, mock_context):
        """Test transformation with all document fields."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "pubmed_id": 12345678,
            "doi": "10.1000/test",
            "patent_id": "US1234567",
            "title": "Full Title",
            "authors": "Author1, Author2",
            "abstract": "Test abstract text",
            "doc_type": "PUBLICATION",
            "journal": "Journal Name",
            "journal_full_title": "Full Journal Name",
            "year": 2024,
            "volume": "10",
            "issue": "5",
            "first_page": "100",
            "last_page": "110",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["journal_full_title"] == "Full Journal Name"
        assert result["src_id"] == 1


@pytest.mark.unit
class TestMoleculeTransformer:
    """Tests for MoleculeTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create MoleculeTransformer instance."""
        return MoleculeTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid molecule record."""
        record = {
            "molecule_chembl_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "first_approval": 1950,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["molecule_chembl_id"] == "CHEMBL25"
        assert result["pref_name"] == "ASPIRIN"
        assert result["molecule_type"] == "Small molecule"
        assert result["max_phase"] == 4
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_chembl_id is missing."""
        record = {
            "pref_name": "TEST MOLECULE",
            "molecule_type": "Small molecule",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_flags(self, transformer, mock_context):
        """Test transformation with boolean flag fields."""
        record = {
            "molecule_chembl_id": "CHEMBL123",
            "oral": True,
            "parenteral": False,
            "topical": False,
            "black_box_warning": 1,
            "natural_product": 0,
            "first_in_class": 1,
            "prodrug": 0,
            "therapeutic_flag": True,
            "withdrawn_flag": False,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["oral"] is True
        assert result["black_box_warning"] == 1

    @pytest.mark.asyncio
    async def test_transform_with_complex_fields(self, transformer, mock_context):
        """Test transformation with complex JSON fields."""
        record = {
            "molecule_chembl_id": "CHEMBL123",
            "molecule_hierarchy": {"parent_chembl_id": "CHEMBL123"},
            "molecule_properties": {"mw_freebase": 180.16},
            "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            "molecule_synonyms": [{"synonym": "Aspirin"}],
            "cross_references": [{"xref_src": "Wikipedia"}],
            "atc_classifications": ["N02BA01"],
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        # JSON fields should be serialized
        assert isinstance(result.get("molecule_hierarchy"), str)
        assert isinstance(result.get("molecule_properties"), str)


@pytest.mark.unit
class TestTargetTransformer:
    """Tests for TargetTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create TargetTransformer instance."""
        return TargetTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid target record."""
        record = {
            "target_chembl_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "tax_id": 9606,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert result["target_chembl_id"] == "CHEMBL1862"
        assert result["pref_name"] == "Cyclooxygenase-2"
        assert result["target_type"] == "SINGLE PROTEIN"
        assert result["tax_id"] == 9606
        assert "entity_id" in result
        assert "content_hash" in result

    @pytest.mark.asyncio
    async def test_transform_missing_target_id(self, transformer, mock_context):
        """Test transformation returns None when target_chembl_id is missing."""
        record = {
            "pref_name": "TEST TARGET",
            "organism": "Homo sapiens",
        }

        result = await transformer.transform(mock_context, record)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_components(self, transformer, mock_context):
        """Test transformation with target components."""
        record = {
            "target_chembl_id": "CHEMBL123",
            "target_components": [{"component_type": "PROTEIN", "accession": "P12345"}],
            "cross_references": [{"xref_src": "UniProt", "xref_id": "P12345"}],
            "species_group_flag": True,
        }

        result = await transformer.transform(mock_context, record)

        assert result is not None
        assert isinstance(result.get("target_components"), str)
        assert isinstance(result.get("cross_references"), str)

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = TargetTransformer(provider="custom_target_provider")
        record = {"target_chembl_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record)

        assert result is not None
