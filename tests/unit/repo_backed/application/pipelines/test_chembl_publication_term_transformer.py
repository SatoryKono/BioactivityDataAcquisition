# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
"""Unit tests for the ChEMBL publication-term transformer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.composition.bootstrap.runtime.classification_init import (
    initialize_publication_type_classification,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = pytest.mark.repo_backed


@pytest.fixture(scope="module", autouse=True)
def initialize_publication_classification() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    initialize_publication_type_classification(repo_root / "configs")


@pytest.fixture
def mock_context():
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite(
            "test_chembl_publication_term_transformer"
        ),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPublicationTermTransformer:
    """Tests for PublicationTermTransformer."""

    @pytest.fixture
    def transformer(self):
        return PublicationTermTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    def test_extract_mesh_terms(self, transformer):
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
        assert len(terms) == 3
        aspirin_heading = next(
            t
            for t in terms
            if t["term"] == "Aspirin" and t["term_type"] == "MESH_HEADING"
        )
        assert aspirin_heading["publication_id"] == "CHEMBL1135642"
        assert aspirin_heading["mesh_id"] == "D001241"
        assert aspirin_heading["qualifier"] == "pharmacology"
        qualifier_term = next(
            t
            for t in terms
            if t["term"] == "pharmacology" and t["term_type"] == "MESH_QUALIFIER"
        )
        assert qualifier_term["publication_id"] == "CHEMBL1135642"
        humans_heading = next(
            t
            for t in terms
            if t["term"] == "Humans" and t["term_type"] == "MESH_HEADING"
        )
        assert humans_heading["mesh_id"] == "D006801"
        assert humans_heading["qualifier"] is None

    def test_term_transformer__extract_keywords__c78e6185(self, transformer):
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
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": [{"mesh_id": "D001241", "mesh_heading": "Aspirin"}],
            "keywords": ["kinase inhibitor"],
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 2
        mesh_terms = [t for t in terms if t["term_type"] == "MESH_HEADING"]
        keyword_terms = [t for t in terms if t["term_type"] == "KEYWORD"]
        assert len(mesh_terms) == 1
        assert len(keyword_terms) == 1

    def test_extract_empty_terms(self, transformer):
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": [],
            "keywords": [],
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 0

    def test_extract_null_terms(self, transformer):
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": None,
            "keywords": None,
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 0

    def test_extract_terms_with_whitespace(self, transformer):
        record = {
            "publication_id": "CHEMBL1234567",
            "keywords": ["  aspirin  ", " kinase inhibitor "],
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 2
        assert terms[0]["term"] == "aspirin"
        assert terms[1]["term"] == "kinase inhibitor"

    def test_compute_term_entity_id_deterministic(self, transformer):
        id1 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
        id2 = transformer.compute_term_entity_id("CHEMBL123", "MESH_HEADING", "Aspirin")
        assert id1 == id2
        assert len(id1) == 16

    def test_compute_term_entity_id_normalizes_html_and_whitespace(self, transformer):
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
        id1 = transformer.compute_term_entity_id("CHEMBL123", "KEYWORD", "aspirin")
        id2 = transformer.compute_term_entity_id("CHEMBL456", "KEYWORD", "aspirin")
        assert id1 != id2

    def test_skip_empty_keywords(self, transformer):
        record = {
            "publication_id": "CHEMBL1234567",
            "keywords": ["aspirin", "", "  ", "kinase"],
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 2
        term_texts = [t["term"] for t in terms]
        assert "aspirin" in term_texts
        assert "kinase" in term_texts

    def test_skip_non_dict_mesh_terms(self, transformer):
        record = {
            "publication_id": "CHEMBL1234567",
            "mesh_terms": [
                {"mesh_id": "D001241", "mesh_heading": "Aspirin"},
                "invalid_string",
                None,
                123,
            ],
        }
        terms = transformer.extract_terms_from_document(record, "CHEMBL1234567")
        assert len(terms) == 1
        assert terms[0]["term"] == "Aspirin"

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_term_normalizes_whitespace(
        self, transformer, mock_context
    ):
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
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "   ",
            "term_type": "KEYWORD",
        }
        result = await transformer.transform(mock_context, record, index=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_transform_pre_silver_supports_legacy_document_id_fallback(
        self, transformer, mock_context
    ):
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
        record = {
            "publication_id": "CHEMBL1234567",
            "term": "kinase",
            "term_type": "   ",
        }
        result = await transformer.transform(mock_context, record, index=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_transform_mesh_terms_array_strips_and_preserves_mesh_id(
        self, transformer, mock_context
    ):
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
        assert len(terms) == 2
        heading = next(t for t in terms if t["term_type"] == "MESH_HEADING")
        assert heading["term"] == "Aspirin"
        assert heading["mesh_id"] == "D001241"
        assert heading["qualifier"] == "pharmacology"
        qualifier = next(t for t in terms if t["term_type"] == "MESH_QUALIFIER")
        assert qualifier["term"] == "pharmacology"
        assert qualifier["mesh_id"] == "D001241"

    @pytest.mark.asyncio
    async def test_transform_pre_extracted_with_none_mesh_id_and_qualifier(
        self, transformer, mock_context
    ):
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
