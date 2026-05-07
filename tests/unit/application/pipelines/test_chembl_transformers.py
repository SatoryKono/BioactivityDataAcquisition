"""Unit tests for ChEMBL transformers (Assay, Document, Molecule, Target)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture(scope="module", autouse=True)
def initialize_publication_classification() -> None:
    """Bootstrap publication-type classification for publication transformer tests."""
    repo_root = Path(__file__).resolve().parents[4]
    initialize_publication_type_classification(repo_root / "configs")


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
        return AssayTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid assay record."""
        record = {
            "assay_id": "CHEMBL1234567",
            "target_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "bao_format": "BAO_0000218",
            "assay_type": "B",
            "assay_type_description": "Binding",
            "relationship_type": "D",
            "description": "Test assay description",
            "confidence_score": 9,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["assay_id"] == "CHEMBL1234567"
        assert result["target_id"] == "CHEMBL123"
        assert result["publication_id"] == "CHEMBL456"
        assert result["bao_format"] == "BAO_0000218"
        assert result["assay_type"] == "B"
        assert result["assay_type_description"] == "Binding"
        assert result["relationship_type"] == "D"
        assert result["confidence_score"] == 9
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_normalizes_assay_bao_and_organism_fields(
        self, transformer, mock_context
    ):
        """Assay normalization should canonicalize BAO fields and organism text."""
        record = {
            "assay_id": "CHEMBL1234567",
            "target_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "bao_format": " bao:0000357 ",
            "bao_label": " Single Protein Format ",
            "assay_type": "B",
            "assay_type_description": "Binding",
            "relationship_type": "D",
            "description": "Test assay description",
            "confidence_score": 9,
            "assay_organism": "Homo sapiens (Human)",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["bao_format"] == "BAO_0000357"
        assert result["bao_label"] == "single protein format"
        assert result["assay_organism"] == "Homo sapiens"

    @pytest.mark.asyncio
    async def test_transform_pre_silver_keeps_raw_bao_label_until_profile_normalization(
        self, transformer, mock_context
    ):
        """Transformer should stage raw bao_label and let the profile resolve it."""
        record = {
            "assay_id": "CHEMBL1234567",
            "target_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "bao_format": " bao:0000357 ",
            "bao_label": "  noisy label  ",
        }

        staged = await transformer.transform_pre_silver(mock_context, record, index=0)
        assert staged is not None
        assert staged.business_data["bao_label"] == "  noisy label  "
        assert staged.business_data["bao_format"] == " bao:0000357 "

        finalized = await transformer.transform(mock_context, record, index=0)
        assert finalized is not None
        assert finalized["bao_format"] == "BAO_0000357"
        assert finalized["bao_label"] == "single protein format"

    @pytest.mark.asyncio
    async def test_transform_missing_assay_id(self, transformer, mock_context):
        """Test transformation returns None when assay_id is missing."""
        record = {
            "target_id": "CHEMBL123",
            "assay_type": "B",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_json_fields(self, transformer, mock_context):
        """Test transformation handles complex JSON fields."""
        record = {
            "assay_id": "CHEMBL1234567",
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
            "assay_id": "CHEMBL1234567",
            "variant_sequence": {
                "accession": "P12345",
                "isoform": "1",
                "mutation": "V600E",
                "organism": "Homo sapiens",
                "sequence": "MTEYKLVVVGAGGVGKSALT...",
                "tax_id": 9606,  # Source API field name
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
        assert result["variant_taxonomy_id"] == 9606
        # Forensic JSON should also be present
        assert isinstance(result.get("variant_sequence_json"), str)

    @pytest.mark.asyncio
    async def test_transform_with_null_variant(self, transformer, mock_context):
        """Test transformation handles null variant_sequence."""
        record = {
            "assay_id": "CHEMBL1234567",
            "variant_sequence": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["variant_accession"] is None
        assert result["variant_isoform"] is None
        assert result["variant_mutation"] is None
        assert result["variant_organism"] is None
        assert result["variant_sequence"] is None
        assert result["variant_taxonomy_id"] is None
        assert result["variant_sequence_json"] is None

    @pytest.mark.asyncio
    async def test_transform_with_partial_variant(self, transformer, mock_context):
        """Test transformation with partial variant_sequence data."""
        record = {
            "assay_id": "CHEMBL1234567",
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
        assert result["variant_taxonomy_id"] is None

    @pytest.mark.asyncio
    async def test_transform_pre_silver_returns_staged_payload(
        self, transformer, mock_context
    ):
        """Assay transformer should expose staged payloads without content hash."""
        record = {
            "assay_id": "CHEMBL1234567",
            "target_id": "CHEMBL123",
            "publication_id": "CHEMBL456",
            "bao_format": "BAO_0000218",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == "chembl:CHEMBL1234567"
        assert result.business_data["assay_id"] == "CHEMBL1234567"
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = AssayTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {"assay_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result


@pytest.mark.unit
class TestPublicationTransformer:
    """Tests for PublicationTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create PublicationTransformer instance."""
        return PublicationTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid document record."""
        record = {
            "publication_id": "CHEMBL1234567",
            "pubmed_id": "12345678",  # Source API field name
            "doi": "10.1000/test.doi",
            "title": "Test Document Title",
            "authors": "Test Author",
            "journal": "Test Journal",
            "year": 2024,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publication_id"] == "CHEMBL1234567"
        assert result["pmid"] == "12345678"  # Standardized output field name
        assert result["doi"] == "10.1000/test.doi"
        assert result["publication_year"] == 2024
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_document_id(self, transformer, mock_context):
        """Test transformation returns None when publication_id is missing."""
        record = {
            "pubmed_id": "12345678",  # Source API field name
            "title": "Test Document",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_all_fields(self, transformer, mock_context):
        """Test transformation with all document fields."""
        record = {
            "publication_id": "CHEMBL1234567",
            "pubmed_id": "12345678",  # Source API field name
            "doi": "10.1000/test",
            # patent_id excluded from unified publication schema
            "title": "Full Title",
            "authors": "Author1, Author2",
            "abstract": "Test abstract text",
            "doc_type": "PUBLICATION",
            "journal": "Journal Name",
            "year": 2024,
            "volume": "10",
            "issue": "5",
            "first_page": "100",
            "last_page": "110",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publication_type_raw"] == "PUBLICATION"
        assert result["publication_type"] == "journal-article"
        assert result["publication_type_unified"] == "Journal Article"
        assert result["journal"] == "Journal Name"
        assert result["src_id"] == 1
        assert result["_source"] == "chembl"  # System field

    def test_extract_business_data_preserves_raw_publication_type_for_domain_profile(
        self, transformer
    ):
        """Application extraction must not own ChEMBL publication taxonomy mapping."""
        record = {
            "publication_id": "CHEMBL1234567",
            "doc_type": "PUBLICATION",
            "title": "Raw provider type seam",
        }

        result = transformer._extract_business_data(record, "CHEMBL1234567")

        assert result["publication_type_raw"] == "PUBLICATION"
        assert result["publication_type"] == "PUBLICATION"
        assert result["publication_type_unified"] == "PUBLICATION"
        assert result["publication_subclass"] == "PUBLICATION"
        assert result["publication_class"] == "PUBLICATION"

    @pytest.mark.asyncio
    async def test_transform_survives_uninitialized_publication_classification(
        self, transformer, mock_context, monkeypatch
    ):
        """Classification bootstrap drift must not fail the whole publication batch."""
        record = {
            "publication_id": "CHEMBL1234567",
            "doc_type": "PUBLICATION",
            "title": "Fallback classification",
        }

        def _raise_runtime_error(*args: object, **kwargs: object) -> dict[str, str]:
            raise RuntimeError("classification data not initialized")

        monkeypatch.setattr(
            "bioetl.domain.normalization.profiles._profile_publication_normalizers.build_publication_type_classification_payload",
            _raise_runtime_error,
        )

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publication_type_raw"] == "PUBLICATION"
        assert result["publication_type"] == "journal-article"
        assert result["publication_type_unified"] is None
        assert result["publication_subclass"] is None
        assert result["publication_class"] is None

    @pytest.mark.asyncio
    async def test_transform_release_metadata_and_invalid_citations(
        self, transformer, mock_context
    ):
        """Test release metadata extraction and invalid citation count fallback."""
        record = {
            "publication_id": "CHEMBL9000001",
            "title": "Release metadata test",
            "chembl_release": {
                "chembl_release": "34",
                "creation_date": "2026-01-01",
            },
            "citation_count": "not-a-number",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["chembl_release"] == "34"
        assert result["creation_date"] == "2026-01-01"
        assert result["citations_received"] is None

    @pytest.mark.asyncio
    async def test_transform_pre_silver_supports_legacy_document_id_fallback(
        self, transformer, mock_context
    ):
        """Publication staged path should accept document_chembl_id fallback."""
        record = {
            "document_chembl_id": "CHEMBL1234567",
            "title": "Fallback publication",
            "doi": "10.1000/test.doi",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == "chembl:CHEMBL1234567"
        assert result.business_data["publication_id"] == "CHEMBL1234567"
        assert "content_hash" not in result.business_data


@pytest.mark.unit
class TestMoleculeTransformer:
    """Tests for MoleculeTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create MoleculeTransformer instance."""
        return MoleculeTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid molecule record."""
        record = {
            "molecule_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "first_approval": 1950,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["molecule_id"] == "CHEMBL25"
        assert result["pref_name"] == "ASPIRIN"
        assert result["molecule_type"] == "Small molecule"
        assert result["max_phase"] == 4
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_molecule_id(self, transformer, mock_context):
        """Test transformation returns None when molecule_id is missing."""
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
            "molecule_id": "CHEMBL123",
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
            "molecule_id": "CHEMBL123",
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
            "molecule_id": "CHEMBL456",
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
            "molecule_id": "CHEMBL789",
            "withdrawn_flag": True,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["withdrawn_flag"] is True

    @pytest.mark.asyncio
    async def test_transform_with_usan_fields(self, transformer, mock_context):
        """Test transformation with USAN naming fields."""
        record = {
            "molecule_id": "CHEMBL1234",
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
            "molecule_id": "CHEMBL5678",
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
        assert result["logp"] == pytest.approx(2.5)
        assert result["mw_freebase"] == pytest.approx(300.5)
        assert result["ro5_violation_count"] == 1
        assert result["molecular_formula"] == "C15H12O3"
        assert result["ro3_pass"] == "Y"

    @pytest.mark.asyncio
    async def test_transform_with_hierarchy_child(self, transformer, mock_context):
        """Test transformation extracts child_chembl_id from hierarchy."""
        record = {
            "molecule_id": "CHEMBL9999",
            "molecule_hierarchy": {
                "parent_chembl_id": "CHEMBL1000",
                "active_chembl_id": "CHEMBL1001",
                "molecule_id": "CHEMBL9999",
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
        return TargetTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid target record."""
        record = {
            "target_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "tax_id": 9606,  # Source API field name
            "species_group_flag": False,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_id"] == "CHEMBL1862"
        assert result["pref_name"] == "Cyclooxygenase-2"
        assert result["target_type"] == "SINGLE PROTEIN"
        assert result["organism"] == "Homo sapiens"
        assert result["species_group_flag"] is False
        assert result["taxonomy_id"] == 9606  # Standardized output field name
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_target_id(self, transformer, mock_context):
        """Test transformation returns None when target_id is missing."""
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
            "target_id": "CHEMBL123",
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
            "target_id": "CHEMBL240",
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
            "target_id": "CHEMBL456",
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
            "target_id": "CHEMBL789",
            "target_components": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cross_references"] is None

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = TargetTransformer(
            provider="custom_target_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {"target_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None

    @pytest.mark.asyncio
    async def test_transform_with_downgraded_field(self, transformer, mock_context):
        """Test transformation extracts downgraded field."""
        record = {
            "target_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
            "downgraded": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["downgraded"] is False

    def test_extract_business_data_preserves_raw_downgraded_for_domain_profile(
        self, transformer
    ):
        """Application extraction must not collapse invalid or missing bool lexemes."""
        for raw_value in ("0", "1", True, False, None, "not-a-bool"):
            record = {
                "target_id": "CHEMBL1862",
                "downgraded": raw_value,
            }

            result = transformer._extract_business_data(record, "CHEMBL1862")

            assert result["downgraded"] is raw_value

    @pytest.mark.asyncio
    async def test_transform_with_pipeline_stages(self, transformer, mock_context):
        """Test transformation handles pipeline_stages as JSON."""
        record = {
            "target_id": "CHEMBL240",
            "pipeline_stages": [{"stage": "Phase 1", "status": "Active"}],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert isinstance(result.get("pipeline_stages"), str)
        import json

        stages = json.loads(result["pipeline_stages"])
        # Single-element lists are unwrapped by serialize_json
        assert isinstance(stages, dict)
        assert stages["stage"] == "Phase 1"

    @pytest.mark.asyncio
    async def test_transform_handles_missing_fields_gracefully(
        self, transformer, mock_context
    ):
        """Test transformation handles missing fields (returns None/defaults)."""
        record = {
            "target_id": "CHEMBL123",
            "pref_name": "Test Target",
            # No downgraded, pipeline_stages
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["downgraded"] is None
        assert result["pipeline_stages"] is None

    @pytest.mark.asyncio
    async def test_transform_organism_class_multicellular(
        self, transformer, mock_context
    ):
        """Test organism_class is set to multicellular for Homo sapiens."""
        record = {
            "target_id": "CHEMBL1862",
            "organism": "Homo sapiens",
            "tax_id": 9606,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_class"] == "multicellular"

    @pytest.mark.asyncio
    async def test_transform_normalizes_organism_to_canonical_display(
        self, transformer, mock_context
    ):
        """Known organism drift should collapse to a canonical display value."""
        record = {
            "target_id": "CHEMBL1862",
            "organism": "  homo sapiens (Human)  ",
            "tax_id": 9606,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism"] == "Homo sapiens"

    @pytest.mark.asyncio
    async def test_transform_normalizes_organism_alias_to_scientific_name(
        self, transformer, mock_context
    ):
        """Common organism aliases should resolve before downstream classification."""
        record = {
            "target_id": "CHEMBL2000",
            "organism": "e. coli",
            "tax_id": 562,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism"] == "Escherichia coli"
        assert result["organism_class"] == "unicellular"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("raw_organism", "tax_id", "expected_organism", "expected_class"),
        [
            (
                "Homo\n        sapiens",
                9606,
                "Homo sapiens",
                "multicellular",
            ),
            (
                "Candida albicans (strain SC5314 / ATCC MYA-2876) (Yeast)",
                5476,
                "Candida albicans",
                "unicellular",
            ),
            (
                "Influenza A virus (strain A/Udorn/1972 H3N2)",
                11320,
                "Influenza A virus",
                None,
            ),
            (
                "Mycobacterium tuberculosis (strain ATCC 25618 / H37Rv)",
                1773,
                "Mycobacterium tuberculosis",
                "unicellular",
            ),
        ],
    )
    async def test_transform_normalizes_historical_vcr_organism_variants(
        self,
        transformer,
        mock_context,
        raw_organism,
        tax_id,
        expected_organism,
        expected_class,
    ):
        """Historical target-organism variants from VCR should normalize deterministically."""
        record = {
            "target_id": f"CHEMBL-{tax_id}",
            "organism": raw_organism,
            "tax_id": tax_id,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism"] == expected_organism
        assert result["organism_class"] == expected_class

    @pytest.mark.asyncio
    async def test_transform_organism_class_unicellular(
        self, transformer, mock_context
    ):
        """Test organism_class is set to unicellular for E. coli."""
        record = {
            "target_id": "CHEMBL2000",
            "organism": "Escherichia coli",
            "tax_id": 562,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_class"] == "unicellular"

    @pytest.mark.asyncio
    async def test_transform_organism_class_acellular(self, transformer, mock_context):
        """Test organism_class is set to acellular for HIV-1."""
        record = {
            "target_id": "CHEMBL3000",
            "organism": "Human immunodeficiency virus 1",
            "tax_id": 11676,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_class"] == "acellular"

    @pytest.mark.asyncio
    async def test_transform_organism_class_none_when_unresolved(
        self, transformer, mock_context
    ):
        """Test organism_class is None when organism cannot be classified."""
        record = {
            "target_id": "CHEMBL4000",
            # No organism or tax_id
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_class"] is None

    @pytest.mark.asyncio
    async def test_transform_organism_class_from_name_only(
        self, transformer, mock_context
    ):
        """Test organism_class can be resolved from organism name without tax_id."""
        record = {
            "target_id": "CHEMBL5000",
            "organism": "Mus musculus",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["organism_class"] == "multicellular"

    @pytest.mark.asyncio
    async def test_transform_preserves_valid_taxonomy_id(
        self, transformer, mock_context
    ):
        """Test taxonomy_id is preserved when tax_id is valid."""
        record = {
            "target_id": "CHEMBL6000",
            "organism": "Homo sapiens",
            "tax_id": "9606",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["taxonomy_id"] == 9606

    @pytest.mark.asyncio
    async def test_transform_invalid_taxonomy_id_becomes_none(
        self, transformer, mock_context
    ):
        """Test invalid tax_id is normalized to None rather than failing."""
        record = {
            "target_id": "CHEMBL7000",
            "organism": "Homo sapiens",
            "tax_id": "invalid-tax-id",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["taxonomy_id"] is None


@pytest.mark.unit
class TestTargetComponentTransformer:
    """Tests for TargetComponentTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create TargetComponentTransformer instance."""
        return TargetComponentTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid target component record."""
        record = {
            "component_id": 123,
            "accession": "P12345",
            "component_type": "PROTEIN",
            "description": "Test Component",
            "organism": "Homo sapiens",
            "tax_id": 9606,  # Source API field name
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["component_id"] == 123
        assert result["accession"] == "P12345"
        assert result["component_type"] == "PROTEIN"
        assert result["taxonomy_id"] == 9606  # Standardized output field name
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

        # Check flattened IDs list (serialized as canonical JSON string)
        assert result["protein_classification_ids"] == "[1015,422]"

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
class TestPublicationTermTransformer:
    """Tests for PublicationTermTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create PublicationTermTransformer instance."""
        return PublicationTermTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    def test_extract_mesh_terms(self, transformer):
        """Test extraction of MeSH terms from document record."""
        record = {
            "publication_id": "CHEMBL1135642",
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
        assert aspirin_heading["publication_id"] == "CHEMBL1135642"
        assert aspirin_heading["mesh_id"] == "D001241"
        assert aspirin_heading["qualifier"] == "pharmacology"

        # Check MeSH qualifier extracted as separate term
        qualifier_term = next(
            t
            for t in terms
            if t["term"] == "pharmacology" and t["term_type"] == "MESH_QUALIFIER"
        )
        assert qualifier_term["publication_id"] == "CHEMBL1135642"

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
            "publication_id": "CHEMBL1135642",
            "keywords": ["aspirin", "anti-inflammatory", "COX inhibitor"],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1135642")

        assert len(terms) == 3

        for term in terms:
            assert term["term_type"] == "KEYWORD"
            assert term["publication_id"] == "CHEMBL1135642"
            assert term["mesh_id"] is None
            assert term["qualifier"] is None

        term_texts = [t["term"] for t in terms]
        assert "aspirin" in term_texts
        assert "anti-inflammatory" in term_texts
        assert "COX inhibitor" in term_texts

    def test_extract_mixed_terms(self, transformer):
        """Test extraction of both MeSH and keywords from document."""
        record = {
            "publication_id": "CHEMBL1234567",
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
            "publication_id": "CHEMBL1234567",
            "mesh_terms": [],
            "keywords": [],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 0

    def test_extract_null_terms(self, transformer):
        """Test extraction from document with null term arrays."""
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": None,
            "keywords": None,
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        assert len(terms) == 0

    def test_extract_terms_with_whitespace(self, transformer):
        """Test that keyword terms are stripped of whitespace."""
        record = {
            "publication_id": "CHEMBL1234567",
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

    def test_compute_term_entity_id_normalizes_html_and_whitespace(self, transformer):
        """Canonical title normalization should keep HTML/whitespace variants stable."""
        id1 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
        id2 = transformer.compute_term_entity_id(
            "CHEMBL123",
            "MESH_HEADING",
            "  Aspirin  ",
        )
        id3 = transformer.compute_term_entity_id(
            "CHEMBL123",
            "MESH_HEADING",
            "<b>Aspirin</b>",
        )

        assert id1 == id2 == id3

    def test_compute_term_entity_id_uses_canonical_profile_identity_sequence(
        self, transformer
    ):
        """Identity must follow the same canonicalization seam as the profile."""
        canonical = transformer.compute_term_entity_id(
            "CHEMBL123",
            "KEYWORD",
            "Kinase Inhibitor",
        )
        semantic_variant = transformer.compute_term_entity_id(
            " chembl123 ",
            " keyword ",
            "  <b>Kinase   Inhibitor</b>  ",
        )

        assert canonical == semantic_variant

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
            "publication_id": "CHEMBL1234567",
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
            "publication_id": "CHEMBL1234567",
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

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_term_normalizes_whitespace(
        self, transformer, mock_context
    ):
        """Test that pre-extracted term records have whitespace stripped.

        This tests the Case 1 branch in _extract_business_data where term
        and term_type come directly from the record (PublicationTermDataSource).
        """
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "  kinase  ",
            "term_type": "  KEYWORD  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["term"] == "kinase"
        assert result["term_type"] == "KEYWORD"
        assert result["publication_id"] == "CHEMBL1234567"

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_mesh_heading_with_qualifier(
        self, transformer, mock_context
    ):
        """Test that pre-extracted MeSH heading preserves mesh_id and qualifier.

        Verifies that the normalization in Case 1 branch doesn't lose
        mesh_id or qualifier fields while applying strip().
        """
        record = {
            "publication_id": "CHEMBL1135642",
            "term": "  Aspirin  ",
            "term_type": "  MESH_HEADING  ",
            "mesh_id": "  D001241  ",
            "qualifier": "  pharmacology  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["term"] == "Aspirin"
        assert result["term_type"] == "MESH_HEADING"
        assert result["mesh_id"] == "D001241"
        assert result["qualifier"] == "pharmacology"
        assert result["publication_id"] == "CHEMBL1135642"

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_empty_term_returns_none(
        self, transformer, mock_context
    ):
        """Test that pre-extracted record with empty term after strip returns None.

        When term is empty or whitespace-only, the base transformer's
        validation should reject the record (skip logic).
        """
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "   ",  # Only whitespace
            "term_type": "KEYWORD",
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Empty term should trigger skip logic in base transformer
        assert result is None

    @pytest.mark.asyncio
    async def test_transform_pre_silver_supports_legacy_document_id_fallback(
        self, transformer, mock_context
    ):
        """PublicationTerm staged path should accept document_chembl_id fallback."""
        record = {
            "document_chembl_id": "CHEMBL1135642",
            "term": "  kinase  ",
            "term_type": "  KEYWORD  ",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert str(result.business_data["publication_id"]).upper() == "CHEMBL1135642"
        assert result.business_data["term"] == "kinase"
        assert result.business_data["term_type"] == "KEYWORD"
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_transform_pre_silver_canonicalizes_term_type_before_entity_id(
        self, transformer, mock_context
    ):
        """Staged publication-term identity must use canonical term_type semantics."""
        record = {
            "publication_id": "CHEMBL1135642",
            "term": "Aspirin",
            "term_type": " keyword ",
        }

        pre_silver = await transformer.transform_pre_silver(
            mock_context, record, index=0
        )

        assert isinstance(pre_silver, PreSilverRecord)
        assert str(pre_silver.business_data["term_type"]).upper() == "KEYWORD"
        assert pre_silver.entity_id == transformer.compute_term_entity_id(
            "CHEMBL1135642",
            "KEYWORD",
            "Aspirin",
        )

    @pytest.mark.asyncio
    async def test_transform_pre_silver_recomputes_entity_id_from_canonical_term_payload(
        self, transformer, mock_context
    ):
        """Staged identity should ignore stale upstream ids and use normalized fields."""
        record = {
            "entity_id": "deadbeefdeadbeef",
            "publication_id": " chembl1135642 ",
            "term": "  <b>aspirin</b>  ",
            "term_type": " keyword ",
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == transformer.compute_term_entity_id(
            "CHEMBL1135642",
            "KEYWORD",
            "aspirin",
        )

    @pytest.mark.asyncio
    async def test_transform_pre_silver_returns_none_when_no_terms_are_extracted(
        self, transformer, mock_context
    ):
        """No derived publication_term row should be staged for termless publications."""
        record = {
            "publication_id": "CHEMBL1135642",
            "mesh_terms": [],
            "keywords": [],
        }

        result = await transformer.transform_pre_silver(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_matches_staged_finalization(
        self, transformer, mock_context
    ):
        """Legacy publication-term transform should match staged finalization."""
        record = {
            "document_chembl_id": "CHEMBL1135642",
            "term": "  aspirin  ",
            "term_type": "  KEYWORD  ",
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
        assert legacy_result["publication_id"] == staged_result["publication_id"]
        assert legacy_result["term"] == staged_result["term"] == "aspirin"
        assert legacy_result["term_type"] == staged_result["term_type"] == "KEYWORD"
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_returns_none_when_no_terms_are_extracted(
        self, transformer, mock_context
    ):
        """Legacy publication-term transform should skip publications without terms."""
        record = {
            "publication_id": "CHEMBL1135642",
            "mesh_terms": [],
            "keywords": [],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_empty_term_type_returns_none(
        self, transformer, mock_context
    ):
        """Test that pre-extracted record with empty term_type returns None.

        When term_type is empty or whitespace-only, the record should be
        skipped as it lacks required classification.
        """
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "kinase",
            "term_type": "   ",  # Only whitespace
        }

        result = await transformer.transform(mock_context, record, index=0)

        # Empty term_type should trigger skip logic
        assert result is None

    @pytest.mark.asyncio
    async def test_transform_mesh_terms_array_strips_and_preserves_mesh_id(
        self, transformer, mock_context
    ):
        """Test extraction from mesh_terms array strips whitespace and preserves mesh_id.

        This tests the Case 2 branch where terms are extracted from nested arrays.
        Verifies consistency with the pre-extracted term normalization.
        """
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": [
                {
                    "mesh_id": "D001241",
                    "mesh_heading": "  Aspirin  ",
                    "mesh_qualifier": "  pharmacology  ",
                },
            ],
        }

        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")

        # Should extract 2 terms: heading + qualifier
        assert len(terms) == 2

        heading = next(t for t in terms if t["term_type"] == "MESH_HEADING")
        assert heading["term"] == "Aspirin"  # Stripped
        assert heading["mesh_id"] == "D001241"
        assert heading["qualifier"] == "  pharmacology  "  # Qualifier preserved as-is

        qualifier = next(t for t in terms if t["term_type"] == "MESH_QUALIFIER")
        assert qualifier["term"] == "pharmacology"  # Stripped
        assert qualifier["mesh_id"] == "D001241"

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_with_none_mesh_id_and_qualifier(
        self, transformer, mock_context
    ):
        """Test that pre-extracted record with None mesh_id/qualifier works correctly."""
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "  kinase inhibitor  ",
            "term_type": "KEYWORD",
            "mesh_id": None,
            "qualifier": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["term"] == "kinase inhibitor"
        assert result["term_type"] == "KEYWORD"
        assert result["mesh_id"] is None
        assert result["qualifier"] is None

    @pytest.mark.asyncio
    async def test_transform_accepts_document_chembl_id_alias(
        self, transformer, mock_context
    ):
        """Test that document_chembl_id is accepted as publication_id alias."""
        record = {
            "document_chembl_id": "CHEMBL7777777",
            "term": "aspirin",
            "term_type": "KEYWORD",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["publication_id"] == "CHEMBL7777777"

    @pytest.mark.asyncio
    async def test_transform_recomputes_entity_id_from_canonical_term_payload(
        self, transformer, mock_context
    ):
        """Transformer must ignore stale upstream entity_id values."""
        record = {
            "publication_id": "CHEMBL1135642",
            "term": "aspirin",
            "term_type": "KEYWORD",
            "entity_id": "precomputed-id-123",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entity_id"] == transformer.compute_term_entity_id(
            "CHEMBL1135642",
            "KEYWORD",
            "aspirin",
        )

    def test_extract_business_data_empty_when_no_nested_terms(self, transformer):
        """Test fallback payload when raw record has no extractable terms."""
        business_data = transformer._extract_business_data(
            {
                "publication_id": "CHEMBL5555555",
                "mesh_terms": [],
                "keywords": [],
            },
            "CHEMBL5555555",
        )

        assert business_data["publication_id"] == "CHEMBL5555555"
        assert business_data["term"] == ""
        assert business_data["term_type"] == ""
        assert business_data["mesh_id"] is None
        assert business_data["qualifier"] is None
