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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for ChEMBL Publication Similarity Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite(
            "test_publication_similarity_transformer"
        ),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPublicationSimilarityTransformer:
    """Tests for PublicationSimilarityTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create PublicationSimilarityTransformer instance."""
        return PublicationSimilarityTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_similarity_transformer__valid_record__67a9eec6(
        self, transformer, mock_context
    ):
        """Test transformation of valid document similarity record."""
        record = {
            "sim_id": 1,
            "doc_1": 12345,
            "doc_2": 12346,
            "tid_tani": 0.8,
            "mol_tani": 0.6,
            "pubmed_id1": 12345678,
            "pubmed_id2": 87654321,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sim_id"] == 1
        assert result["doc_1"] == 12345
        assert result["doc_2"] == 12346
        assert result["tid_tani"] == pytest.approx(0.8)
        assert result["mol_tani"] == pytest.approx(0.6)
        # PMID should be normalized to string
        assert result["pubmed_id1"] == "12345678"
        assert result["pubmed_id2"] == "87654321"
        # Verify derived metrics
        assert result["avg_tani"] == pytest.approx(0.7)
        assert result["max_tani"] == pytest.approx(0.8)
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_sim_id(self, transformer, mock_context):
        """Test transformation returns None when sim_id is missing."""
        record = {
            "doc_1": 12345,
            "doc_2": 12346,
            "tid_tani": 0.8,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_similarity_transformer__minimal_record__d840cf75(
        self, transformer, mock_context
    ):
        """Test transformation with only required fields."""
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sim_id"] == 1
        assert result["doc_1"] == 100
        assert result["doc_2"] == 200
        assert result["tid_tani"] is None
        assert result["mol_tani"] is None
        assert result["avg_tani"] is None
        assert result["max_tani"] is None
        assert result["pubmed_id1"] is None
        assert result["pubmed_id2"] is None

    @pytest.mark.asyncio
    async def test_transform_both_tanimoto_present(self, transformer, mock_context):
        """Test derived metrics when both Tanimoto coefficients present."""
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": 0.8,
            "mol_tani": 0.6,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["avg_tani"] == pytest.approx(0.7)  # (0.8 + 0.6) / 2
        assert result["max_tani"] == pytest.approx(0.8)  # max(0.8, 0.6)

    @pytest.mark.asyncio
    async def test_transform_only_tid_tani_present(self, transformer, mock_context):
        """Test derived metrics when only tid_tani present."""
        record = {
            "sim_id": 2,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": 0.75,
            "mol_tani": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["avg_tani"] == pytest.approx(0.75)
        assert result["max_tani"] == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_transform_only_mol_tani_present(self, transformer, mock_context):
        """Test derived metrics when only mol_tani present."""
        record = {
            "sim_id": 3,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": None,
            "mol_tani": 0.9,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["avg_tani"] == pytest.approx(0.9)
        assert result["max_tani"] == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_transform_no_tanimoto_present(self, transformer, mock_context):
        """Test derived metrics when no Tanimoto coefficients present."""
        record = {
            "sim_id": 4,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": None,
            "mol_tani": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["avg_tani"] is None
        assert result["max_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_tanimoto_as_string(self, transformer, mock_context):
        """Test that Tanimoto values as strings are converted to floats."""
        record = {
            "sim_id": 5,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": "0.85",
            "mol_tani": "0.65",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["tid_tani"] == pytest.approx(0.85)
        assert result["mol_tani"] == pytest.approx(0.65)
        assert result["avg_tani"] == pytest.approx(0.75)  # (0.85 + 0.65) / 2

    @pytest.mark.asyncio
    async def test_transform_ids_as_string(self, transformer, mock_context):
        """Test that integer IDs as strings are converted appropriately.

        sim_id, doc_1, doc_2 are converted to int.
        pubmed_id1, pubmed_id2 are normalized to string.
        """
        record = {
            "sim_id": "123",
            "doc_1": "100",
            "doc_2": "200",
            "pubmed_id1": "12345678",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["sim_id"] == 123
        assert result["doc_1"] == 100
        assert result["doc_2"] == 200
        # PMID should remain as string (normalized)
        assert result["pubmed_id1"] == "12345678"

    def test_similarity_transformer__primary_id_field__06ea502f(self, transformer):
        """Test primary ID field is set correctly."""
        assert transformer.primary_id_field == "sim_id"

    def test_entity_class(self, transformer):
        """Test entity class is set correctly."""
        from bioetl.domain.entities import ChemblPublicationSimilarity

        assert transformer.entity_class is ChemblPublicationSimilarity

    @pytest.mark.asyncio
    async def test_similarity_transformer__content_hash__2ee7404d(
        self, transformer, mock_context
    ):
        """Test that content_hash is generated and is 64 hex characters."""
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64
        # Verify it's a valid hex string
        int(result["content_hash"], 16)

    @pytest.mark.asyncio
    async def test_similarity_transformer__lineage_fields__6a303349(
        self, transformer, mock_context
    ):
        """Test that all lineage fields are present."""
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert result["_source_batch_id"] is None
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_similarity_transformer__custom_provider__d4c9be39(
        self, mock_context
    ):
        """Test transformation with custom provider."""
        transformer = PublicationSimilarityTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result

    @pytest.mark.asyncio
    async def test_transform_rounding_precision(self, transformer, mock_context):
        """Test that derived metrics are rounded to 6 decimal places."""
        record = {
            "sim_id": 1,
            "doc_1": 100,
            "doc_2": 200,
            "tid_tani": 0.123456789,
            "mol_tani": 0.987654321,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # Average: (0.123456789 + 0.987654321) / 2 = 0.555555555
        assert result["avg_tani"] == pytest.approx(0.555556)  # Rounded to 6 decimals
        assert result["max_tani"] == pytest.approx(0.987654)  # Rounded to 6 decimals
