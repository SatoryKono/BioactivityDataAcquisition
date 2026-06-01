"""Unit tests for ChEMBL transformers (Assay, Document, Molecule, Target)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
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

pytestmark = pytest.mark.repo_backed


def _minimal_valid_assay_record() -> dict[str, object]:
    return {
        "assay_id": "CHEMBL1234567",
        "target_id": "CHEMBL123",
        "publication_id": "CHEMBL456",
        "bao_format": "BAO_0000218",
        "assay_type": "B",
        "assay_type_description": "Binding",
        "relationship_type": "D",
        "description": "Test assay description",
        "confidence_score": 9,
        "src_id": 1,
    }


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
    async def test_assay_transformer__valid_record__506ed965(self, transformer, mock_context):
        """Test transformation of valid assay record."""
        record = _minimal_valid_assay_record()

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["assay_id"] == "CHEMBL1234567"
        assert result["target_id"] == "CHEMBL123"
        assert result["publication_id"] == "CHEMBL456"
        assert result["bao_format"] == "BAO_0000218"
        assert result["assay_type"] == "B"
        assert result["assay_type_description"] == "Binding"
        assert result["assay_description"] == "Test assay description"
        assert "description" not in result
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
            **_minimal_valid_assay_record(),
            "bao_format": " bao:0000357 ",
            "bao_label": " Single Protein Format ",
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
            **_minimal_valid_assay_record(),
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
            **_minimal_valid_assay_record(),
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
            **_minimal_valid_assay_record(),
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
        record = {**_minimal_valid_assay_record(), "variant_sequence": None}

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
            **_minimal_valid_assay_record(),
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
    async def test_assay_transformer__custom_provider__82f39279(self, mock_context):
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
    async def test_transformer__valid_record__64865dfa(self, transformer, mock_context):
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
        assert result["journal"] == "Journal Name"
        assert result["src_id"] == 1
        assert result["_source"] == "chembl"  # System field
        for field_name in (
            "pmc_id",
            "publication_type_unified",
            "publication_subclass",
            "publication_class",
            "oa_status",
            "citations_received",
            "citations_made",
            "affiliation_list",
            "author_orcids",
            "is_oa",
            "issn_list",
            "language",
            "publication_date",
        ):
            assert field_name not in result

    def test_extract_business_data_preserves_raw_publication_type_for_domain_profile(
        self, transformer
    ):
        """Application extraction keeps the raw seam and defers taxonomy mapping."""
        record = {
            "publication_id": "CHEMBL1234567",
            "doc_type": "PUBLICATION",
            "title": "Raw provider type seam",
        }

        result = transformer._extract_business_data(record, "CHEMBL1234567")

        assert result["publication_type_raw"] == "PUBLICATION"
        assert result["publication_type"] is None
        assert result["publication_type_unified"] is None
        assert result["publication_subclass"] is None
        assert result["publication_class"] is None

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
        assert "publication_type_unified" not in result
        assert "publication_subclass" not in result
        assert "publication_class" not in result

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
        assert "citations_received" not in result

    @pytest.mark.asyncio
    async def test_transformer__document_id_fallback__540d6faa(
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
    async def test_molecule_transformer__valid_record__8613ed54(self, transformer, mock_context):
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
    async def test_target_transformer__valid_record__1b7799a9(self, transformer, mock_context):
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
        assert result["target_protein_synonyms"] == "unknown"
        assert result["target_gene_synonyms"] == "unknown"
        assert result["target_ec_numbers"] == "unknown"

    @pytest.mark.asyncio
    async def test_transform_does_not_emit_target_level_protein_class_summary(
        self, transformer, mock_context
    ):
        """Target summary fields now belong to the relation/composite surfaces."""
        record = {
            "target_id": "CHEMBL123",
            "target_components": [
                {
                    "component_id": 10,
                    "protein_classifications": [
                        {
                            "protein_classification_id": 1015,
                            "l1_id": 1,
                            "l1_name": "Enzyme",
                            "l1_desc": "Root",
                            "l2_id": 2,
                            "l2_name": "Protease",
                            "l2_desc": "Branch",
                        }
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "protein_classifications" not in result
        assert "target_protein_class_id_L1" not in result
        assert "target_protein_class_name_L1" not in result

    @pytest.mark.asyncio
    async def test_transform_ignores_prepared_target_protein_classification_rows(
        self, transformer, mock_context
    ):
        """Prepared relation rows no longer backfill the base target contract."""
        record = {
            "target_id": "CHEMBL123",
            "target_components": [{"component_id": 10}],
            "target_protein_classifications": [
                {
                    "target_id": "CHEMBL123",
                    "component_id": 10,
                    "leaf_id": 1015,
                    "classification_status": "resolved",
                    "l1_id": 1,
                    "l1_name": "Enzyme",
                    "l1_desc": "Root",
                    "l2_id": 2,
                    "l2_name": "Kinase",
                    "l2_desc": "Branch",
                    "l3_id": 1015,
                    "l3_name": "Serine/threonine kinase",
                    "l3_desc": "Leaf",
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "protein_classifications" not in result
        assert "target_protein_class_id_L1" not in result
        assert "target_protein_class_name_L3" not in result

    @pytest.mark.asyncio
    async def test_transform_leaves_multifunctional_projection_to_relation_summary(
        self, transformer, mock_context
    ):
        """Multifunctional resolution is no longer a responsibility of chembl_target."""
        record = {
            "target_id": "CHEMBL123",
            "target_components": [
                {
                    "component_id": 10,
                    "protein_classifications": [
                        {
                            "protein_classification_id": 148,
                            "l1_id": 3,
                            "l1_name": "Membrane receptor",
                            "l2_id": 7,
                            "l2_name": "Ion channel",
                        },
                        {
                            "protein_classification_id": 12,
                            "l1_id": 1,
                            "l1_name": "Enzyme",
                            "l2_id": 2,
                            "l2_name": "Kinase",
                        },
                    ],
                },
                {
                    "component_id": 11,
                    "protein_classifications": [
                        {
                            "protein_classification_id": 148,
                            "l1_name": "duplicate ignored",
                        }
                    ],
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "protein_classifications" not in result
        assert "target_protein_class_name_L1" not in result
        assert "target_protein_class_name_L3" not in result

    @pytest.mark.asyncio
    async def test_transform_omits_protein_classification_summary_when_missing(
        self, transformer, mock_context
    ):
        """Base target rows omit relation-owned fields when no classification exists."""
        record = {
            "target_id": "CHEMBL123",
            "target_components": [
                {"component_id": 10, "component_type": "PROTEIN"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "protein_classifications" not in result
        assert "target_protein_class_id_L1" not in result
        assert "target_protein_class_name_L1" not in result

    @pytest.mark.asyncio
    async def test_transform_projects_derived_component_synonyms(
        self, transformer, mock_context
    ):
        """Target synonym categories should project from raw nested component payloads."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "component_id": 1,
                    "target_component_synonyms": [
                        {
                            "component_synonym": " Alpha protein ",
                            "syn_type": "uniprot",
                        },
                        {
                            "component_synonym": "A|B",
                            "syn_type": "UNIPROT",
                        },
                        {
                            "component_synonym": "GENE1",
                            "syn_type": "GENE_SYMBOL",
                        },
                        {
                            "component_synonym": "GENE1",
                            "syn_type": "GENE_SYMBOL_OTHER",
                        },
                        {
                            "component_synonym": " GENE2 ",
                            "syn_type": "GENE_SYMBOL_OTHER",
                        },
                        {
                            "component_synonym": "1.2.3.4",
                            "syn_type": "EC_NUMBER",
                        },
                        {
                            "component_synonym": "1.2.3.4",
                            "syn_type": "EC_NUMBER",
                        },
                        {
                            "component_synonym": "ignored",
                            "syn_type": "OTHER",
                        },
                        {
                            "component_synonym": " ",
                            "syn_type": "UNIPROT",
                        },
                    ],
                },
                {
                    "component_id": 2,
                    "target_component_synonyms": [
                        {
                            "component_synonym": "Alpha protein",
                            "syn_type": "UNIPROT",
                        },
                        {
                            "component_synonym": "GENE3",
                            "syn_type": "GENE_SYMBOL_ALIAS",
                        },
                    ],
                },
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_protein_synonyms"] == "Alpha protein|A\\|B"
        assert result["target_gene_synonyms"] == "GENE1|GENE2|GENE3"
        assert result["target_ec_numbers"] == "1.2.3.4"
        assert isinstance(result["target_component_synonyms"], str)
        assert "Alpha protein" in result["target_component_synonyms"]
        assert "GENE3" in result["target_component_synonyms"]

    @pytest.mark.asyncio
    async def test_transform_projects_unknown_when_component_synonyms_missing(
        self, transformer, mock_context
    ):
        """Derived synonym fields should fall back to the missing sentinel."""
        record = {
            "target_id": "CHEMBL999",
            "target_components": [
                {
                    "component_id": 1,
                    "target_component_synonyms": [
                        {
                            "component_synonym": None,
                            "syn_type": "UNIPROT",
                        },
                        {
                            "component_synonym": "  ",
                            "syn_type": "GENE_SYMBOL",
                        },
                    ],
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_protein_synonyms"] == "unknown"
        assert result["target_gene_synonyms"] == "unknown"
        assert result["target_ec_numbers"] == "unknown"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("source_db", "xref_id", "xref_name", "expected_field", "expected_value"),
        [
            ("PDB", "1ABC", "ignored for pdb", "target_xref_pdb_ids", "1ABC"),
            ("PDBe", "2XYZ", "ignored for pdbe", "target_xref_pdb_ids", "2XYZ"),
            (
                "GoComponent",
                "GO:0005887",
                "plasma membrane",
                "target_xref_go_component",
                "plasma membrane",
            ),
            (
                "GoFunction",
                "GO:0004911",
                "dopamine receptor activity",
                "target_xref_go_function",
                "dopamine receptor activity",
            ),
            (
                "GoProcess",
                "GO:0038110",
                "dopamine receptor signaling pathway",
                "target_xref_go_process",
                "dopamine receptor signaling pathway",
            ),
            (
                "Reactome",
                "R-HSA-5673001",
                "ignored for reactome",
                "target_xref_reactome_ids",
                "R-HSA-5673001",
            ),
            (
                "HGNC",
                "HGNC:6008",
                "IL2RA",
                "target_xref_hgnc_ids",
                "HGNC:6008",
            ),
            (
                "UniProt",
                "P01589",
                "Interleukin-2 receptor subunit alpha",
                "target_xref_uniprot_ids",
                "P01589",
            ),
        ],
    )
    async def test_transform_projects_target_xref_source_aliases(
        self,
        transformer,
        mock_context,
        source_db,
        xref_id,
        xref_name,
        expected_field,
        expected_value,
    ):
        """Alias variants for supported xref sources must project into the expected column."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {
                            "xref_id": xref_id,
                            "xref_name": xref_name,
                            "xref_src_db": source_db,
                        },
                        {"xref_id": "9999", "xref_src_db": "UnknownSource"},
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result[expected_field] == expected_value
        assert "target_xref_iuphar_ids" not in result
        assert result["target_xref_pdb_ids"] == (
            expected_value if expected_field == "target_xref_pdb_ids" else "unknown"
        )
        assert result["target_xref_go_component"] == (
            expected_value
            if expected_field == "target_xref_go_component"
            else "unknown"
        )
        assert result["target_xref_go_function"] == (
            expected_value
            if expected_field == "target_xref_go_function"
            else "unknown"
        )
        assert result["target_xref_go_process"] == (
            expected_value
            if expected_field == "target_xref_go_process"
            else "unknown"
        )
        assert result["target_xref_hgnc_ids"] == (
            expected_value if expected_field == "target_xref_hgnc_ids" else "unknown"
        )
        assert result["target_xref_reactome_ids"] == (
            expected_value
            if expected_field == "target_xref_reactome_ids"
            else "unknown"
        )
        assert result["target_xref_uniprot_ids"] == (
            expected_value
            if expected_field == "target_xref_uniprot_ids"
            else "unknown"
        )
        if expected_field == "target_xref_hgnc_ids":
            assert "IL2RA" not in result["target_xref_hgnc_ids"]
        if expected_field == "target_xref_uniprot_ids":
            assert "Interleukin" not in result["target_xref_uniprot_ids"]
        # Preserve source-of-record in forensic payload
        import json

        cross_references = json.loads(result["cross_references"])
        assert isinstance(cross_references, list)
        raw_sources = {xref["xref_src_db"] for xref in cross_references}
        assert {source_db, "UnknownSource"} <= {str(v) for v in raw_sources}

    @pytest.mark.asyncio
    async def test_transform_deduplicates_and_orders_target_xrefs(self, transformer, mock_context):
        """Projection should deduplicate projected values and preserve first-seen order."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {"xref_id": "  1ABC  ", "xref_src_db": "PDB"},
                        {"xref_id": "Q99999", "xref_src_db": "PDB"},
                        {"xref_id": "1ABC", "xref_src_db": "PDBe"},
                        {"xref_id": "P|2", "xref_src_db": "PDBe"},
                        {
                            "xref_id": "GO:0005887",
                            "xref_name": " plasma membrane ",
                            "xref_src_db": "GoComponent",
                        },
                        {
                            "xref_id": "GO:0098590",
                            "xref_name": "plasma membrane",
                            "xref_src_db": "GoComponent",
                        },
                        {
                            "xref_id": "GO:0004911",
                            "xref_name": "dopamine receptor activity",
                            "xref_src_db": "GoFunction",
                        },
                        {
                            "xref_id": "HGNC:6008",
                            "xref_name": "IL2RA",
                            "xref_src_db": "HGNC",
                        },
                        {
                            "xref_id": "HGNC:6008",
                            "xref_name": "duplicate ignored",
                            "xref_src_db": "HGNC",
                        },
                        {
                            "xref_id": "6009",
                            "xref_name": "IL2RB",
                            "xref_src_db": "HGNC",
                        },
                        {
                            "xref_id": "P01589",
                            "xref_name": "Interleukin-2 receptor subunit alpha",
                            "xref_src_db": "UniProt",
                        },
                        {
                            "xref_id": "Q99999",
                            "xref_name": "duplicate allowed in another bucket",
                            "xref_src_db": "UniProt",
                        },
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_xref_pdb_ids"] == "1ABC|Q99999|P\\|2"
        assert result["target_xref_go_component"] == "plasma membrane"
        assert result["target_xref_go_function"] == "dopamine receptor activity"
        assert result["target_xref_hgnc_ids"] == "HGNC:6008|6009"
        assert result["target_xref_uniprot_ids"] == "P01589|Q99999"
        assert result["target_xref_reactome_ids"] == "unknown"
        assert result["target_xref_go_process"] == "unknown"
        assert "target_xref_iuphar_ids" not in result

        import json

        cross_references = json.loads(result["cross_references"])
        xref_ids = [item["xref_id"] for item in cross_references]
        assert xref_ids == [
            "  1ABC  ",
            "Q99999",
            "1ABC",
            "P|2",
            "GO:0005887",
            "GO:0098590",
            "GO:0004911",
            "HGNC:6008",
            "HGNC:6008",
            "6009",
            "P01589",
            "Q99999",
        ]

    @pytest.mark.asyncio
    async def test_transform_returns_unknown_for_empty_hgnc_uniprot_xref_ids(
        self, transformer, mock_context
    ):
        """HGNC/UniProt buckets must ignore blank IDs instead of falling back to names."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {
                            "xref_id": " ",
                            "xref_name": "IL2RA",
                            "xref_src_db": "HGNC",
                        },
                        {
                            "xref_id": "",
                            "xref_name": "Interleukin-2 receptor subunit alpha",
                            "xref_src_db": "UniProt",
                        },
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_xref_hgnc_ids"] == "unknown"
        assert result["target_xref_uniprot_ids"] == "unknown"

    @pytest.mark.asyncio
    async def test_transform_keeps_removed_iuphar_sources_only_in_cross_references(
        self, transformer, mock_context
    ):
        """Removed IUPHAR-family sources must stay only in forensic cross_references."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {"xref_id": "1839", "xref_src_db": "GuideToPharmacology"},
                        {"xref_id": "UNK-1", "xref_src_db": "LegacyDB"},
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "target_xref_iuphar_ids" not in result
        assert result["target_xref_pdb_ids"] == "unknown"
        assert result["target_xref_go_component"] == "unknown"
        assert result["target_xref_go_function"] == "unknown"
        assert result["target_xref_go_process"] == "unknown"
        assert result["target_xref_hgnc_ids"] == "unknown"
        assert result["target_xref_reactome_ids"] == "unknown"
        assert result["target_xref_uniprot_ids"] == "unknown"

        import json

        cross_references = json.loads(result["cross_references"])
        raw_sources = {xref["xref_src_db"] for xref in cross_references}
        assert raw_sources == {"GuideToPharmacology", "LegacyDB"}

    @pytest.mark.asyncio
    async def test_transform_skips_general_go_and_unknown_xref_sources_from_projection(
        self, transformer, mock_context
    ):
        """General GO and unknown source labels are preserved only in cross_references."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {"xref_id": "GO:1234", "xref_src_db": "GO"},
                        {"xref_id": "UNK-1", "xref_src_db": "LegacyDB"},
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "target_xref_iuphar_ids" not in result
        assert result["target_xref_pdb_ids"] == "unknown"
        assert result["target_xref_go_component"] == "unknown"
        assert result["target_xref_go_function"] == "unknown"
        assert result["target_xref_go_process"] == "unknown"
        assert result["target_xref_hgnc_ids"] == "unknown"
        assert result["target_xref_reactome_ids"] == "unknown"
        assert result["target_xref_uniprot_ids"] == "unknown"

        import json

        cross_references = json.loads(result["cross_references"])
        raw_sources = {xref["xref_src_db"] for xref in cross_references}
        assert raw_sources == {"GO", "LegacyDB"}

    @pytest.mark.asyncio
    async def test_transform_uses_go_xref_name_without_fallback_to_xref_id(
        self, transformer, mock_context
    ):
        """GO-derived buckets must use xref_name and ignore xref_id when the name is blank."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {
                    "target_component_xrefs": [
                        {
                            "xref_id": "GO:0005887",
                            "xref_name": "  plasma membrane  ",
                            "xref_src_db": "GoComponent",
                        },
                        {
                            "xref_id": "GO:0004911",
                            "xref_name": "   ",
                            "xref_src_db": "GoFunction",
                        },
                        {
                            "xref_id": "GO:0038110",
                            "xref_src_db": "GoProcess",
                        },
                    ]
                }
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_xref_go_component"] == "plasma membrane"
        assert result["target_xref_go_function"] == "unknown"
        assert result["target_xref_go_process"] == "unknown"
        assert result["target_xref_hgnc_ids"] == "unknown"
        assert result["target_xref_reactome_ids"] == "unknown"
        assert result["target_xref_uniprot_ids"] == "unknown"
        assert "target_xref_iuphar_ids" not in result

    @pytest.mark.asyncio
    async def test_transform_returns_unknown_when_no_target_component_xrefs(
        self, transformer, mock_context
    ):
        """No component xrefs should emit unknown sentinel for all derived xref columns."""
        record = {
            "target_id": "CHEMBL240",
            "target_components": [
                {"accession": "P12345", "component_type": "PROTEIN"},
            ],
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "target_xref_iuphar_ids" not in result
        assert result["target_xref_pdb_ids"] == "unknown"
        assert result["target_xref_go_component"] == "unknown"
        assert result["target_xref_go_function"] == "unknown"
        assert result["target_xref_go_process"] == "unknown"
        assert result["target_xref_hgnc_ids"] == "unknown"
        assert result["target_xref_reactome_ids"] == "unknown"
        assert result["target_xref_uniprot_ids"] == "unknown"
        assert result["cross_references"] is None

    @pytest.mark.asyncio
    async def test_transform_projects_description_to_target_description(
        self, transformer, mock_context
    ):
        """Silver output must expose target_description, not the domain alias."""
        record = {
            "target_id": "CHEMBL1862",
            "description": "Prostaglandin G/H synthase 2",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["target_description"] == "Prostaglandin G/H synthase 2"
        assert "description" not in result

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
    async def test_target_transformer__custom_provider__03da38ad(self, mock_context):
        """Test transformation with custom provider."""
        transformer = TargetTransformer(
            provider="custom_target_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {"target_id": "CUSTOM123"}

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None

    @pytest.mark.asyncio
    async def test_transform_handles_missing_fields_gracefully(
        self, transformer, mock_context
    ):
        """Test transformation handles missing fields (returns None/defaults)."""
        record = {
            "target_id": "CHEMBL123",
            "pref_name": "Test Target",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "downgraded" not in result
        assert "pipeline_stages" not in result
        assert result["target_components"] is None
        assert result["cross_references"] is None
        assert result["target_component_synonyms"] is None

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
                "acellular",
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
    async def test_component_transformer__valid_record__ff1e0627(self, transformer, mock_context):
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
    async def test_component_transformer__with_json_fields__cb5ce019(self, transformer, mock_context):
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
