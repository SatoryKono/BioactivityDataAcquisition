"""Unit tests for ChEMBL transformers (Assay, Document, Molecule, Target)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document_term_transformer import (
    DocumentTermTransformer,
)
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


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

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["assay_chembl_id"] == "CHEMBL1234567"
        assert result["target_chembl_id"] == "CHEMBL123"
        assert result["assay_type"] == "B"
        assert result["confidence_score"] == 9
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_assay_id(self, transformer, mock_context):
        """Test transformation returns None when assay_chembl_id is missing."""
        record = {
            "target_chembl_id": "CHEMBL123",
            "assay_type": "B",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_json_fields(self, transformer, mock_context):
        """Test transformation handles complex JSON fields."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "assay_classifications": [{"class": "Pharmacology"}],
            "assay_parameters": [{"param": "IC50"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # JSON fields should be serialized as strings
        assert isinstance(result.get("assay_classifications"), str)
        assert isinstance(result.get("assay_parameters"), str)

    @pytest.mark.asyncio
    async def test_transform_with_variant_sequence(self, transformer, mock_context):
        """Test transformation with variant_sequence data (flattened structure)."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "variant_sequence": {
                "accession": "P12345",
                "isoform": "1",
                "mutation": "V600E",
                "organism": "Homo sapiens",
                "sequence": "MTEYKLVVVGAGGVGKSALT...",
                "tax_id": 9606,
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Flattened variant fields
        assert result["variant_accession"] == "P12345"
        assert result["variant_isoform"] == "1"
        assert result["variant_mutation"] == "V600E"
        assert result["variant_organism"] == "Homo sapiens"
        assert result["variant_sequence"] == "MTEYKLVVVGAGGVGKSALT..."
        assert result["variant_tax_id"] == 9606
        # Forensic JSON should also be present
        assert isinstance(result.get("variant_sequence_json"), str)

    @pytest.mark.asyncio
    async def test_transform_with_null_variant(self, transformer, mock_context):
        """Test transformation handles null variant_sequence."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "variant_sequence": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["variant_accession"] is None
        assert result["variant_isoform"] is None
        assert result["variant_mutation"] is None
        assert result["variant_organism"] is None
        assert result["variant_sequence"] is None
        assert result["variant_tax_id"] is None
        assert result["variant_sequence_json"] is None

    @pytest.mark.asyncio
    async def test_transform_with_partial_variant(self, transformer, mock_context):
        """Test transformation with partial variant_sequence data."""
        record = {
            "assay_chembl_id": "CHEMBL1234567",
            "variant_sequence": {
                "accession": "P12345",
                "mutation": "L858R",
                # Other fields missing
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["variant_accession"] == "P12345"
        assert result["variant_mutation"] == "L858R"
        assert result["variant_isoform"] is None
        assert result["variant_organism"] is None
        assert result["variant_sequence"] is None
        assert result["variant_tax_id"] is None

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = AssayTransformer(provider="custom_provider")
        record = {"assay_chembl_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record, index=0)

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

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["document_chembl_id"] == "CHEMBL1234567"
        # PMID is normalized to string for cross-provider consistency
        assert result["pubmed_id"] == "12345678"
        assert result["doi"] == "10.1000/test.doi"
        assert result["year"] == 2024
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_document_id(self, transformer, mock_context):
        """Test transformation returns None when document_chembl_id is missing."""
        record = {
            "pubmed_id": 12345678,
            "title": "Test Document",
        }

        result = await transformer.transform(mock_context, record, index=0)

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

        result = await transformer.transform(mock_context, record, index=0)

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

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_chembl_id"] == "CHEMBL25"
        assert result["pref_name"] == "ASPIRIN"
        assert result["molecule_type"] == "Small molecule"
        assert result["max_phase"] == 4
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_chembl_id is missing."""
        record = {
            "pref_name": "TEST MOLECULE",
            "molecule_type": "Small molecule",
        }

        result = await transformer.transform(mock_context, record, index=0)

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

        result = await transformer.transform(mock_context, record, index=0)

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

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # JSON fields should be serialized
        assert isinstance(result.get("molecule_hierarchy"), str)
        assert isinstance(result.get("molecule_properties"), str)

    @pytest.mark.asyncio
    async def test_transform_with_new_core_fields(self, transformer, mock_context):
        """Test transformation with chirality, availability_type, and other new fields."""
        record = {
            "molecule_chembl_id": "CHEMBL456",
            "chirality": 1,  # racemic
            "dosed_ingredient": 1,
            "availability_type": 2,
            "molecule_species": "NEUTRAL",
            "helm_notation": "PEPTIDE1{A.G.K}$$$$",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["chirality"] == 1
        assert result["dosed_ingredient"] == 1
        assert result["availability_type"] == 2
        assert result["molecule_species"] == "NEUTRAL"
        assert result["helm_notation"] == "PEPTIDE1{A.G.K}$$$$"

    @pytest.mark.asyncio
    async def test_transform_with_withdrawn_flag(self, transformer, mock_context):
        """Test transformation with withdrawn_flag field.

        Note: withdrawn_year, withdrawn_country, withdrawn_reason are not available
        in the /molecule endpoint. Use /drug_warning endpoint for detailed info.
        """
        record = {
            "molecule_chembl_id": "CHEMBL789",
            "withdrawn_flag": True,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["withdrawn_flag"] is True

    @pytest.mark.asyncio
    async def test_transform_with_usan_fields(self, transformer, mock_context):
        """Test transformation with USAN naming fields."""
        record = {
            "molecule_chembl_id": "CHEMBL1234",
            "usan_stem": "-mab",
            "usan_stem_definition": "monoclonal antibody",
            "usan_substem": "-xi-",
            "usan_year": 2015,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["usan_stem"] == "-mab"
        assert result["usan_stem_definition"] == "monoclonal antibody"
        assert result["usan_substem"] == "-xi-"
        assert result["usan_year"] == 2015

    @pytest.mark.asyncio
    async def test_transform_with_extended_properties(self, transformer, mock_context):
        """Test transformation with extended property fields.

        Note: acd_logd, acd_logp, acd_most_apka, acd_most_bpka are not available
        in the public ChEMBL API.
        """
        record = {
            "molecule_chembl_id": "CHEMBL5678",
            "molecule_properties": {
                "alogp": 2.5,
                "mw_freebase": 300.5,
                "num_ro5_violations": 1,
                "full_molformula": "C15H12O3",
                "ro3_pass": "Y",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["property_alogp"] == 2.5
        assert result["property_mw_freebase"] == 300.5
        assert result["property_ro5_violations"] == 1
        assert result["property_full_molformula"] == "C15H12O3"
        assert result["property_ro3_pass"] == "Y"

    @pytest.mark.asyncio
    async def test_transform_with_hierarchy_child(self, transformer, mock_context):
        """Test transformation extracts child_chembl_id from hierarchy."""
        record = {
            "molecule_chembl_id": "CHEMBL9999",
            "molecule_hierarchy": {
                "parent_chembl_id": "CHEMBL1000",
                "active_chembl_id": "CHEMBL1001",
                "molecule_chembl_id": "CHEMBL9999",
            },
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["hierarchy_parent_chembl_id"] == "CHEMBL1000"
        assert result["hierarchy_active_chembl_id"] == "CHEMBL1001"
        assert result["hierarchy_child_chembl_id"] == "CHEMBL9999"


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

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_chembl_id"] == "CHEMBL1862"
        assert result["pref_name"] == "Cyclooxygenase-2"
        assert result["target_type"] == "SINGLE PROTEIN"
        assert result["tax_id"] == 9606
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_target_id(self, transformer, mock_context):
        """Test transformation returns None when target_chembl_id is missing."""
        record = {
            "pref_name": "TEST TARGET",
            "organism": "Homo sapiens",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_components(self, transformer, mock_context):
        """Test transformation with target components containing xrefs."""
        record = {
            "target_chembl_id": "CHEMBL123",
            "target_components": [
                {
                    "component_type": "PROTEIN",
                    "accession": "P12345",
                    "target_component_xrefs": [
                        {"xref_id": "P12345", "xref_src_db": "UniProt"},
                    ],
                }
            ],
            "cross_references": [],  # API always returns empty at target level
            "species_group_flag": True,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert isinstance(result.get("target_components"), str)
        assert isinstance(result.get("cross_references"), str)
        # Verify xrefs are aggregated from components
        import json

        xrefs = json.loads(result["cross_references"])
        # Single-element lists are unwrapped by serialize_json
        # So xrefs is a dict, not a list
        assert isinstance(xrefs, dict)
        assert xrefs["xref_id"] == "P12345"
        assert xrefs["xref_src_db"] == "UniProt"

    @pytest.mark.asyncio
    async def test_transform_aggregates_xrefs_from_multiple_components(
        self, transformer, mock_context
    ):
        """Test that cross_references are aggregated from all target_component_xrefs."""
        record = {
            "target_chembl_id": "CHEMBL240",
            "cross_references": [],  # API always returns empty
            "target_components": [
                {
                    "accession": "Q12809",
                    "component_type": "PROTEIN",
                    "target_component_xrefs": [
                        {"xref_id": "Q12809", "xref_src_db": "UniProt"},
                        {
                            "xref_id": "HGNC:6251",
                            "xref_name": "KCNH2",
                            "xref_src_db": "HGNC",
                        },
                    ],
                },
                {
                    "accession": "P00533",
                    "component_type": "PROTEIN",
                    "target_component_xrefs": [
                        {"xref_id": "P00533", "xref_src_db": "UniProt"},
                    ],
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        import json

        xrefs = json.loads(result["cross_references"])
        assert len(xrefs) == 3  # Aggregated from both components
        xref_ids = [x["xref_id"] for x in xrefs]
        assert "Q12809" in xref_ids
        assert "HGNC:6251" in xref_ids
        assert "P00533" in xref_ids

    @pytest.mark.asyncio
    async def test_transform_handles_components_without_xrefs(
        self, transformer, mock_context
    ):
        """Test handling of targets with components but no cross-references."""
        record = {
            "target_chembl_id": "CHEMBL456",
            "target_components": [
                {"accession": "P12345", "component_type": "PROTEIN"}  # No xrefs
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cross_references"] is None

    @pytest.mark.asyncio
    async def test_transform_handles_empty_components(self, transformer, mock_context):
        """Test handling of targets with no components."""
        record = {
            "target_chembl_id": "CHEMBL789",
            "target_components": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cross_references"] is None

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = TargetTransformer(provider="custom_target_provider")
        record = {"target_chembl_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None

    @pytest.mark.asyncio
    async def test_transform_with_new_metadata_fields(self, transformer, mock_context):
        """Test transformation extracts new metadata fields (description, downgraded, dap_id)."""
        record = {
            "target_chembl_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "description": "Prostaglandin G/H synthase 2",
            "downgraded": 0,
            "dap_id": 12345,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["description"] == "Prostaglandin G/H synthase 2"
        assert result["downgraded"] is False
        assert result["dap_id"] == 12345

    @pytest.mark.asyncio
    async def test_transform_with_pipeline_stages_and_constraints(
        self, transformer, mock_context
    ):
        """Test transformation handles pipeline_stages and target_constraints as JSON."""
        record = {
            "target_chembl_id": "CHEMBL240",
            "pipeline_stages": [{"stage": "Phase 1", "status": "Active"}],
            "target_constraints": [{"constraint_type": "assay"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert isinstance(result.get("pipeline_stages"), str)
        assert isinstance(result.get("target_constraints"), str)
        import json

        stages = json.loads(result["pipeline_stages"])
        # Single-element lists are unwrapped by serialize_json
        assert isinstance(stages, dict)
        assert stages["stage"] == "Phase 1"

    @pytest.mark.asyncio
    async def test_transform_extracts_component_organisms_and_tax_ids(
        self, transformer, mock_context
    ):
        """Test transformation extracts organisms and tax_ids from components."""
        record = {
            "target_chembl_id": "CHEMBL2111431",
            "target_components": [
                {
                    "accession": "P12345",
                    "component_id": 100,
                    "component_type": "PROTEIN",
                    "organism": "Homo sapiens",
                    "tax_id": 9606,
                },
                {
                    "accession": "P67890",
                    "component_id": 101,
                    "component_type": "PROTEIN",
                    "organism": "Mus musculus",
                    "tax_id": 10090,
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["component_organisms"] == ["Homo sapiens", "Mus musculus"]
        assert result["component_tax_ids"] == [9606, 10090]

    @pytest.mark.asyncio
    async def test_transform_handles_missing_new_fields_gracefully(
        self, transformer, mock_context
    ):
        """Test transformation handles missing new fields (returns None)."""
        record = {
            "target_chembl_id": "CHEMBL123",
            "pref_name": "Test Target",
            # No description, downgraded, dap_id, pipeline_stages, target_constraints
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["description"] is None
        assert result["downgraded"] is False  # Default value
        assert result["dap_id"] is None
        assert result["pipeline_stages"] is None
        assert result["target_constraints"] is None


@pytest.mark.unit
class TestTargetComponentTransformer:
    """Tests for TargetComponentTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create TargetComponentTransformer instance."""
        return TargetComponentTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid target component record."""
        record = {
            "component_id": 123,
            "accession": "P12345",
            "component_type": "PROTEIN",
            "description": "Test Component",
            "organism": "Homo sapiens",
            "tax_id": 9606,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["component_id"] == 123
        assert result["accession"] == "P12345"
        assert result["component_type"] == "PROTEIN"
        assert result["tax_id"] == 9606
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_component_id(self, transformer, mock_context):
        """Test transformation returns None when component_id is missing."""
        record = {
            "accession": "P12345",
            "component_type": "PROTEIN",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_json_fields(self, transformer, mock_context):
        """Test transformation handles complex JSON fields."""
        record = {
            "component_id": 123,
            "target_component_synonyms": [{"synonym": "Synonym1"}],
            "target_component_xrefs": [{"xref_id": "X123"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert isinstance(result.get("target_component_synonyms"), str)
        assert isinstance(result.get("target_component_xrefs"), str)

    @pytest.mark.asyncio
    async def test_transform_with_protein_classifications(
        self, transformer, mock_context
    ):
        """Test transformation extracts protein_classifications as JSON and IDs list.

        Note: ChEMBL API only returns protein_classification_id in this endpoint.
        pref_name and short_name are available via /protein_classification/{id}.
        """
        record = {
            "component_id": 456,
            "accession": "P12345",
            "protein_classifications": [
                {"protein_classification_id": 1015},
                {"protein_classification_id": 422},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None

        # Check JSON forensic field is preserved
        assert isinstance(result.get("protein_classifications"), str)
        import json

        classifications = json.loads(result["protein_classifications"])
        assert len(classifications) == 2
        assert classifications[0]["protein_classification_id"] == 1015
        assert classifications[1]["protein_classification_id"] == 422

        # Check flattened IDs list
        assert result["protein_classification_ids"] == [1015, 422]

    @pytest.mark.asyncio
    async def test_transform_with_empty_protein_classifications(
        self, transformer, mock_context
    ):
        """Test transformation handles empty/None protein_classifications."""
        # Test with None
        record_none = {"component_id": 789, "accession": "Q99999"}
        result_none = await transformer.transform(mock_context, record_none, index=0)
        assert result_none is not None
        assert result_none.get("protein_classification_ids") is None

        # Test with empty list
        record_empty = {
            "component_id": 790,
            "accession": "Q99998",
            "protein_classifications": [],
        }
        result_empty = await transformer.transform(mock_context, record_empty, index=0)
        assert result_empty is not None
        assert result_empty.get("protein_classification_ids") is None


@pytest.mark.unit
class TestDocumentTermTransformer:
    """Tests for DocumentTermTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create DocumentTermTransformer instance."""
        return DocumentTermTransformer(provider="chembl")

    def test_extract_mesh_terms(self, transformer):
        """Test extraction of MeSH terms from document record."""
        record = {
            "document_chembl_id": "CHEMBL1135642",
            "mesh_terms": [
                {
                    "mesh_id": "D001241",
                    "mesh_heading": "Aspirin",
                    "mesh_qualifier": "pharmacology",
                },
                {
                    "mesh_id": "D006801",
                    "mesh_heading": "Humans",
                },
            ],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1135642")

        # Should extract 3 terms: 2 headings + 1 qualifier
        assert len(terms) == 3

        # Check first MeSH heading
        aspirin_heading = next(
            t
            for t in terms
            if t["term"] == "Aspirin" and t["term_type"] == "MESH_HEADING"
        )
        assert aspirin_heading["document_chembl_id"] == "CHEMBL1135642"
        assert aspirin_heading["mesh_id"] == "D001241"
        assert aspirin_heading["qualifier"] == "pharmacology"

        # Check MeSH qualifier extracted as separate term
        qualifier_term = next(
            t
            for t in terms
            if t["term"] == "pharmacology" and t["term_type"] == "MESH_QUALIFIER"
        )
        assert qualifier_term["document_chembl_id"] == "CHEMBL1135642"

        # Check second MeSH heading (no qualifier)
        humans_heading = next(
            t
            for t in terms
            if t["term"] == "Humans" and t["term_type"] == "MESH_HEADING"
        )
        assert humans_heading["mesh_id"] == "D006801"
        assert humans_heading["qualifier"] is None

    def test_extract_keywords(self, transformer):
        """Test extraction of keywords from document record."""
        record = {
            "document_chembl_id": "CHEMBL1135642",
            "keywords": ["aspirin", "anti-inflammatory", "COX inhibitor"],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1135642")

        assert len(terms) == 3

        for term in terms:
            assert term["term_type"] == "KEYWORD"
            assert term["document_chembl_id"] == "CHEMBL1135642"
            assert term["mesh_id"] is None
            assert term["qualifier"] is None

        term_texts = [t["term"] for t in terms]
        assert "aspirin" in term_texts
        assert "anti-inflammatory" in term_texts
        assert "COX inhibitor" in term_texts

    def test_extract_mixed_terms(self, transformer):
        """Test extraction of both MeSH and keywords from document."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "mesh_terms": [
                {"mesh_id": "D001241", "mesh_heading": "Aspirin"},
            ],
            "keywords": ["kinase inhibitor"],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 2

        mesh_terms = [t for t in terms if t["term_type"] == "MESH_HEADING"]
        keyword_terms = [t for t in terms if t["term_type"] == "KEYWORD"]

        assert len(mesh_terms) == 1
        assert len(keyword_terms) == 1

    def test_extract_empty_terms(self, transformer):
        """Test extraction from document with no terms."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "mesh_terms": [],
            "keywords": [],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 0

    def test_extract_null_terms(self, transformer):
        """Test extraction from document with null term arrays."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "mesh_terms": None,
            "keywords": None,
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 0

    def test_extract_terms_with_whitespace(self, transformer):
        """Test that keyword terms are stripped of whitespace."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "keywords": ["  aspirin  ", " kinase inhibitor "],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 2
        assert terms[0]["term"] == "aspirin"
        assert terms[1]["term"] == "kinase inhibitor"

    def test_compute_term_entity_id_deterministic(self, transformer):
        """Test that entity ID computation is deterministic."""
        id1 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
        id2 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")

        assert id1 == id2
        assert len(id1) == 16  # First 16 chars of SHA256

    def test_compute_term_entity_id_case_insensitive(self, transformer):
        """Test that entity ID is case-insensitive for term text."""
        id1 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
        id2 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "aspirin")
        id3 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "ASPIRIN")

        assert id1 == id2 == id3

    def test_compute_term_entity_id_different_for_different_types(self, transformer):
        """Test that different term types produce different IDs."""
        id_heading = transformer.compute_term_entity_id(
            "CHEMBL123", "MESH_HEADING", "aspirin"
        )
        id_keyword = transformer.compute_term_entity_id(
            "CHEMBL123", "KEYWORD", "aspirin"
        )

        assert id_heading != id_keyword

    def test_compute_term_entity_id_different_for_different_documents(
        self, transformer
    ):
        """Test that different documents produce different IDs."""
        id1 = transformer.compute_term_entity_id("CHEMBL123", "KEYWORD", "aspirin")
        id2 = transformer.compute_term_entity_id("CHEMBL456", "KEYWORD", "aspirin")

        assert id1 != id2

    def test_skip_empty_keywords(self, transformer):
        """Test that empty string keywords are skipped."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "keywords": ["aspirin", "", "  ", "kinase"],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        # Only "aspirin" and "kinase" should be extracted
        assert len(terms) == 2
        term_texts = [t["term"] for t in terms]
        assert "aspirin" in term_texts
        assert "kinase" in term_texts

    def test_skip_non_dict_mesh_terms(self, transformer):
        """Test that non-dict entries in mesh_terms are skipped."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "mesh_terms": [
                {"mesh_id": "D001241", "mesh_heading": "Aspirin"},
                "invalid_string",  # Should be skipped
                None,  # Should be skipped
                123,  # Should be skipped
            ],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        # Only the valid dict should be processed
        assert len(terms) == 1
        assert terms[0]["term"] == "Aspirin"
