"""Unit tests for ChEMBL Protein Classification Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.protein_classification_transformer import (
    ProteinClassificationTransformer,
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
class TestProteinClassificationTransformer:
    """Tests for ProteinClassificationTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create ProteinClassificationTransformer instance."""
        return ProteinClassificationTransformer(provider="chembl")

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid protein classification record."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "class_level": 1,
            "pref_name": "Enzyme",
            "short_name": "Enzyme",
            "protein_class_desc": "Protein with catalytic activity",
            "definition": "An enzyme is a protein that catalyzes reactions",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["class_level"] == 1
        assert result["pref_name"] == "Enzyme"
        assert result["short_name"] == "Enzyme"
        assert result["protein_class_desc"] == "Protein with catalytic activity"
        assert result["definition"] == "An enzyme is a protein that catalyzes reactions"
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_protein_class_id(self, transformer, mock_context):
        """Test transformation returns None when protein_class_id is missing."""
        record = {
            "pref_name": "Enzyme",
            "class_level": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_minimal_record(self, transformer, mock_context):
        """Test transformation with only required fields."""
        record = {
            "protein_class_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["class_level"] is None
        assert result["pref_name"] is None
        assert result["short_name"] is None
        assert result["protein_class_desc"] is None
        assert result["definition"] is None

    @pytest.mark.asyncio
    async def test_transform_with_parent_id(self, transformer, mock_context):
        """Test transformation of child classification with parent_id."""
        record = {
            "protein_class_id": 100,
            "parent_id": 1,
            "class_level": 2,
            "pref_name": "Kinase",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 100
        assert result["parent_id"] == 1
        assert result["class_level"] == 2
        assert result["pref_name"] == "Kinase"

    @pytest.mark.asyncio
    async def test_transform_with_whitespace_in_pref_name(
        self, transformer, mock_context
    ):
        """Test that pref_name is stripped of leading/trailing whitespace."""
        record = {
            "protein_class_id": 1,
            "pref_name": "  Enzyme  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pref_name"] == "Enzyme"

    @pytest.mark.asyncio
    async def test_transform_with_empty_text_fields(self, transformer, mock_context):
        """Test that empty string text fields become None."""
        record = {
            "protein_class_id": 1,
            "pref_name": "",
            "short_name": "   ",
            "protein_class_desc": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pref_name"] is None
        assert result["short_name"] is None
        assert result["protein_class_desc"] is None

    @pytest.mark.asyncio
    async def test_transform_strips_text_whitespace(self, transformer, mock_context):
        """Test that text fields are stripped of whitespace."""
        record = {
            "protein_class_id": 1,
            "pref_name": "  Kinase  ",
            "short_name": "\tKin\n",
            "definition": "  A phosphorylating enzyme  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["pref_name"] == "Kinase"
        assert result["short_name"] == "Kin"
        assert result["definition"] == "A phosphorylating enzyme"

    @pytest.mark.asyncio
    async def test_transform_with_invalid_class_level_zero(
        self, transformer, mock_context
    ):
        """Test that class_level of 0 becomes None (must be 1-8)."""
        record = {
            "protein_class_id": 1,
            "class_level": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["class_level"] is None

    @pytest.mark.asyncio
    async def test_transform_with_invalid_class_level_negative(
        self, transformer, mock_context
    ):
        """Test that negative class_level becomes None (must be 1-8)."""
        record = {
            "protein_class_id": 1,
            "class_level": -1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["class_level"] is None

    @pytest.mark.asyncio
    async def test_transform_with_invalid_class_level_too_high(
        self, transformer, mock_context
    ):
        """Test that class_level > 8 becomes None (must be 1-8)."""
        record = {
            "protein_class_id": 1,
            "class_level": 9,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["class_level"] is None

    @pytest.mark.asyncio
    async def test_transform_with_valid_class_levels(self, transformer, mock_context):
        """Test that valid class_levels 1-8 are preserved."""
        for level in range(1, 9):
            record = {
                "protein_class_id": level,
                "class_level": level,
            }

            result = await transformer.transform(mock_context, record, index=0)

            assert result is not None
            assert result["class_level"] == level

    @pytest.mark.asyncio
    async def test_transform_with_invalid_parent_id_zero(
        self, transformer, mock_context
    ):
        """Test that parent_id of 0 becomes None (must be >= 1)."""
        record = {
            "protein_class_id": 1,
            "parent_id": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["parent_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_negative_parent_id(self, transformer, mock_context):
        """Test that negative parent_id becomes None (must be >= 1)."""
        record = {
            "protein_class_id": 1,
            "parent_id": -1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["parent_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_valid_parent_id(self, transformer, mock_context):
        """Test that valid parent_id is preserved."""
        record = {
            "protein_class_id": 100,
            "parent_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["parent_id"] == 1

    @pytest.mark.asyncio
    async def test_transform_with_class_level_as_string(
        self, transformer, mock_context
    ):
        """Test that class_level as string is converted to int."""
        record = {
            "protein_class_id": 1,
            "class_level": "3",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["class_level"] == 3

    @pytest.mark.asyncio
    async def test_transform_custom_provider(self, mock_context):
        """Test transformation with custom provider."""
        transformer = ProteinClassificationTransformer(provider="custom_provider")
        record = {
            "protein_class_id": 123,
            "pref_name": "CustomClass",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result

    @pytest.mark.asyncio
    async def test_transform_generates_content_hash(self, transformer, mock_context):
        """Test that content_hash is generated and is 64 hex characters."""
        record = {
            "protein_class_id": 1,
            "pref_name": "Enzyme",
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
            "protein_class_id": 1,
            "pref_name": "Enzyme",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_source_batch_id" in result
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transform_with_null_values(self, transformer, mock_context):
        """Test transformation handles None values correctly."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "class_level": None,
            "pref_name": None,
            "short_name": None,
            "protein_class_desc": None,
            "definition": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["parent_id"] is None
        assert result["class_level"] is None
        assert result["pref_name"] is None
        assert result["short_name"] is None
        assert result["protein_class_desc"] is None
        assert result["definition"] is None

    @pytest.mark.asyncio
    async def test_transform_root_node(self, transformer, mock_context):
        """Test transformation of a root classification node (class_level=1, no parent)."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "class_level": 1,
            "pref_name": "Protein",
            "short_name": "Protein",
            "definition": "A polypeptide chain of amino acids",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["class_level"] == 1

    @pytest.mark.asyncio
    async def test_transform_leaf_node(self, transformer, mock_context):
        """Test transformation of a leaf classification node (deep in hierarchy)."""
        record = {
            "protein_class_id": 12345,
            "parent_id": 1234,
            "class_level": 7,
            "pref_name": "Tyrosine kinase receptor family member A",
            "short_name": "TrkA",
            "protein_class_desc": "Neurotrophic tyrosine kinase receptor",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 12345
        assert result["parent_id"] == 1234
        assert result["class_level"] == 7
        assert result["pref_name"] == "Tyrosine kinase receptor family member A"
        assert result["short_name"] == "TrkA"
