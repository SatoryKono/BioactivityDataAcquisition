"""Unit tests for ChEMBL Document Similarity Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.document_similarity_transformer import (
    DocumentSimilarityTransformer,
)
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
class TestDocumentSimilarityTransformer:
    """Tests for DocumentSimilarityTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create DocumentSimilarityTransformer instance."""
        return DocumentSimilarityTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid document similarity record."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 0.75,
            "tid_tani": 0.85,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["document_1_chembl_id"] == "CHEMBL1001"
        assert result["document_2_chembl_id"] == "CHEMBL1002"
        assert result["mol_tani"] == 0.75
        assert result["tid_tani"] == 0.85
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_normalizes_pair_order(self, transformer, mock_context):
        """Test that document pairs are normalized (doc1 < doc2)."""
        record = {
            "document_1_chembl_id": "CHEMBL2000",  # Larger
            "document_2_chembl_id": "CHEMBL1000",  # Smaller
            "mol_tani": 0.5,
            "tid_tani": 0.6,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        # After normalization, doc1 should be the smaller one
        assert result["document_1_chembl_id"] == "CHEMBL1000"
        assert result["document_2_chembl_id"] == "CHEMBL2000"

    @pytest.mark.asyncio
    async def test_transform_skips_self_similarity(self, transformer, mock_context):
        """Test that self-similarity records are skipped."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1001",
            "mol_tani": 1.0,
            "tid_tani": 1.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_missing_doc1_id(self, transformer, mock_context):
        """Test transformation returns None when document_1_chembl_id is missing."""
        record = {
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 0.5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_missing_doc2_id(self, transformer, mock_context):
        """Test transformation returns None when document_2_chembl_id is missing."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "mol_tani": 0.5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_minimal_record(self, transformer, mock_context):
        """Test transformation with only document IDs."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["document_1_chembl_id"] == "CHEMBL1001"
        assert result["document_2_chembl_id"] == "CHEMBL1002"
        assert result["mol_tani"] is None
        assert result["tid_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_with_nan_tanimoto(self, transformer, mock_context):
        """Test that NaN Tanimoto values become None."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": float("nan"),
            "tid_tani": float("nan"),
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] is None
        assert result["tid_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_with_inf_tanimoto(self, transformer, mock_context):
        """Test that Inf Tanimoto values become None."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": float("inf"),
            "tid_tani": float("-inf"),
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] is None
        assert result["tid_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_with_out_of_range_tanimoto(
        self, transformer, mock_context
    ):
        """Test that out-of-range Tanimoto values become None."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 1.5,  # > 1
            "tid_tani": -0.5,  # < 0
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] is None
        assert result["tid_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_rounds_tanimoto_values(self, transformer, mock_context):
        """Test that Tanimoto values are rounded to 10 decimals."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 0.123456789012345,
            "tid_tani": 0.987654321098765,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] == round(0.123456789012345, 10)
        assert result["tid_tani"] == round(0.987654321098765, 10)

    @pytest.mark.asyncio
    async def test_transform_boundary_tanimoto_values(self, transformer, mock_context):
        """Test that boundary Tanimoto values (0 and 1) are accepted."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 0.0,
            "tid_tani": 1.0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] == 0.0
        assert result["tid_tani"] == 1.0

    @pytest.mark.asyncio
    async def test_transform_with_whitespace_in_ids(self, transformer, mock_context):
        """Test that document IDs are stripped of whitespace."""
        record = {
            "document_1_chembl_id": "  CHEMBL1001  ",
            "document_2_chembl_id": "\tCHEMBL1002\n",
            "mol_tani": 0.5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["document_1_chembl_id"] == "CHEMBL1001"
        assert result["document_2_chembl_id"] == "CHEMBL1002"

    @pytest.mark.asyncio
    async def test_transform_with_empty_string_ids(self, transformer, mock_context):
        """Test that empty string IDs return None."""
        record = {
            "document_1_chembl_id": "",
            "document_2_chembl_id": "CHEMBL1002",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_string_tanimoto(self, transformer, mock_context):
        """Test that string Tanimoto values are converted to float."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": "0.75",
            "tid_tani": "0.85",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] == 0.75
        assert result["tid_tani"] == 0.85

    @pytest.mark.asyncio
    async def test_transform_with_invalid_string_tanimoto(
        self, transformer, mock_context
    ):
        """Test that invalid string Tanimoto values become None."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": "not_a_number",
            "tid_tani": "invalid",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["mol_tani"] is None
        assert result["tid_tani"] is None

    @pytest.mark.asyncio
    async def test_transform_generates_composite_entity_id(
        self, transformer, mock_context
    ):
        """Test that entity_id is generated with composite key format."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entity_id"] == "chembl:CHEMBL1001_CHEMBL1002"

    @pytest.mark.asyncio
    async def test_transform_generates_content_hash(self, transformer, mock_context):
        """Test that content_hash is generated and is 64 hex characters."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
            "mol_tani": 0.5,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64
        # Verify it's a valid hex string
        int(result["content_hash"], 16)

    @pytest.mark.asyncio
    async def test_transform_includes_lineage_fields(self, transformer, mock_context):
        """Test that all lineage fields are present."""
        record = {
            "document_1_chembl_id": "CHEMBL1001",
            "document_2_chembl_id": "CHEMBL1002",
        }

        result = await transformer.transform(mock_context, record, index=5)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert result["_index"] == 5

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = DocumentSimilarityTransformer(provider="custom_provider")
        record = {
            "document_1_chembl_id": "DOC1",
            "document_2_chembl_id": "DOC2",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["entity_id"] == "custom_provider:DOC1_DOC2"

    @pytest.mark.asyncio
    async def test_normalize_pair_preserves_already_ordered(self, transformer):
        """Test that already ordered pairs are not changed."""
        result = transformer._normalize_pair("CHEMBL1000", "CHEMBL2000")
        assert result == ("CHEMBL1000", "CHEMBL2000")

    @pytest.mark.asyncio
    async def test_normalize_pair_swaps_unordered(self, transformer):
        """Test that unordered pairs are swapped."""
        result = transformer._normalize_pair("CHEMBL2000", "CHEMBL1000")
        assert result == ("CHEMBL1000", "CHEMBL2000")

    @pytest.mark.asyncio
    async def test_validate_tanimoto_valid_values(self, transformer):
        """Test validation of valid Tanimoto values."""
        assert transformer._validate_tanimoto(0.0) == 0.0
        assert transformer._validate_tanimoto(0.5) == 0.5
        assert transformer._validate_tanimoto(1.0) == 1.0

    @pytest.mark.asyncio
    async def test_validate_tanimoto_none(self, transformer):
        """Test validation of None Tanimoto value."""
        assert transformer._validate_tanimoto(None) is None

    @pytest.mark.asyncio
    async def test_validate_tanimoto_invalid(self, transformer):
        """Test validation of invalid Tanimoto values."""
        assert transformer._validate_tanimoto(float("nan")) is None
        assert transformer._validate_tanimoto(float("inf")) is None
        assert transformer._validate_tanimoto(-0.1) is None
        assert transformer._validate_tanimoto(1.1) is None


@pytest.mark.unit
class TestDocumentSimilarityEntity:
    """Tests for DocumentSimilarity entity validation."""

    @pytest.fixture
    def base_entity_fields(self):
        """Provide base entity required fields."""
        from datetime import UTC, datetime

        from bioetl.domain.types import RunType

        return {
            "run_id": uuid4(),
            "run_type": RunType.INCREMENTAL,
            "ingestion_ts": datetime.now(UTC),
            "_index": 0,
        }

    def test_entity_valid_creation(self, base_entity_fields):
        """Test creation of valid DocumentSimilarity entity."""
        from bioetl.domain.entities import DocumentSimilarity

        entity = DocumentSimilarity(
            entity_id="chembl:CHEMBL1_CHEMBL2",
            content_hash="a" * 64,
            document_1_chembl_id="CHEMBL1",
            document_2_chembl_id="CHEMBL2",
            mol_tani=0.5,
            tid_tani=0.7,
            **base_entity_fields,
        )

        assert entity.document_1_chembl_id == "CHEMBL1"
        assert entity.document_2_chembl_id == "CHEMBL2"
        assert entity.mol_tani == 0.5
        assert entity.tid_tani == 0.7

    def test_entity_rejects_self_similarity(self, base_entity_fields):
        """Test that self-similarity is rejected."""
        from bioetl.domain.entities import DocumentSimilarity

        with pytest.raises(ValueError, match="Self-similarity not allowed"):
            DocumentSimilarity(
                entity_id="chembl:CHEMBL1_CHEMBL1",
                content_hash="a" * 64,
                document_1_chembl_id="CHEMBL1",
                document_2_chembl_id="CHEMBL1",
                **base_entity_fields,
            )

    def test_entity_rejects_unnormalized_order(self, base_entity_fields):
        """Test that unnormalized pair order is rejected."""
        from bioetl.domain.entities import DocumentSimilarity

        with pytest.raises(ValueError, match="Pair must be normalized"):
            DocumentSimilarity(
                entity_id="chembl:CHEMBL2_CHEMBL1",
                content_hash="a" * 64,
                document_1_chembl_id="CHEMBL2",
                document_2_chembl_id="CHEMBL1",  # doc1 > doc2 is invalid
                **base_entity_fields,
            )

    def test_entity_rejects_invalid_mol_tani(self, base_entity_fields):
        """Test that invalid mol_tani values are rejected."""
        from bioetl.domain.entities import DocumentSimilarity

        with pytest.raises(ValueError, match="mol_tani must be in"):
            DocumentSimilarity(
                entity_id="chembl:CHEMBL1_CHEMBL2",
                content_hash="a" * 64,
                document_1_chembl_id="CHEMBL1",
                document_2_chembl_id="CHEMBL2",
                mol_tani=1.5,  # > 1 is invalid
                **base_entity_fields,
            )

    def test_entity_rejects_invalid_tid_tani(self, base_entity_fields):
        """Test that invalid tid_tani values are rejected."""
        from bioetl.domain.entities import DocumentSimilarity

        with pytest.raises(ValueError, match="tid_tani must be in"):
            DocumentSimilarity(
                entity_id="chembl:CHEMBL1_CHEMBL2",
                content_hash="a" * 64,
                document_1_chembl_id="CHEMBL1",
                document_2_chembl_id="CHEMBL2",
                tid_tani=-0.5,  # < 0 is invalid
                **base_entity_fields,
            )

    def test_entity_allows_none_tanimoto(self, base_entity_fields):
        """Test that None Tanimoto values are allowed."""
        from bioetl.domain.entities import DocumentSimilarity

        entity = DocumentSimilarity(
            entity_id="chembl:CHEMBL1_CHEMBL2",
            content_hash="a" * 64,
            document_1_chembl_id="CHEMBL1",
            document_2_chembl_id="CHEMBL2",
            mol_tani=None,
            tid_tani=None,
            **base_entity_fields,
        )

        assert entity.mol_tani is None
        assert entity.tid_tani is None
