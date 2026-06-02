"""Unit tests for ChEMBL Protein Classification Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities import ProteinClassification
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


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
class TestProteinClassTransformer:
    """Tests for ProteinClassTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create ProteinClassTransformer instance."""
        return ProteinClassTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    def test_entity_class_is_protein_classification(self, transformer):
        """Verify entity_class is set correctly."""
        assert transformer.entity_class is ProteinClassification

    def test_primary_id_field(self, transformer):
        """Verify primary_id_field is set correctly."""
        assert transformer.primary_id_field == "protein_class_id"

    @pytest.mark.asyncio
    async def test_transform_root_node(self, transformer, mock_context):
        """Test transformation of root node (no parent)."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "pref_name": "Enzyme",
            "short_name": "Enzyme",
            "protein_class_desc": "Enzymes catalyze chemical reactions",
            "definition": "Proteins that catalyze chemical reactions",
            "class_level": 1,
            "sort_order": 1,
            "replaced_by": None,
            "downgraded": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["pref_name"] == "Enzyme"
        assert result["short_name"] == "Enzyme"
        assert result["class_level"] == 1
        assert result["downgraded"] == 0
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_child_node(self, transformer, mock_context):
        """Test transformation of child node with parent."""
        record = {
            "protein_class_id": 100,
            "parent_id": 1,
            "pref_name": "Kinase",
            "short_name": "Kinase",
            "protein_class_desc": "Enzymes that transfer phosphate groups",
            "definition": "Full kinase definition",
            "class_level": 2,
            "sort_order": 10,
            "replaced_by": None,
            "downgraded": 0,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 100
        assert result["parent_id"] == 1
        assert result["class_level"] == 2
        assert result["sort_order"] == 10

    @pytest.mark.asyncio
    async def test_transform_deprecated_node(self, transformer, mock_context):
        """Test transformation of deprecated node."""
        record = {
            "protein_class_id": 50,
            "parent_id": 1,
            "pref_name": "Old Classification",
            "short_name": None,
            "protein_class_desc": None,
            "definition": None,
            "class_level": 2,
            "sort_order": None,
            "replaced_by": 100,
            "downgraded": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["replaced_by"] == 100
        assert result["downgraded"] == 1

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
    async def test_transform_skips_root_classification_record(
        self, transformer, mock_context
    ):
        """The synthetic ChEMBL root node should be skipped before DQ validation."""
        record = {
            "protein_class_id": 0,
            "class_level": 0,
            "pref_name": "Protein class",
            "short_name": "Protein class",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_class_transformer__minimal_record__8008a5c1(
        self, transformer, mock_context
    ):
        """Test transformation with only required fields."""
        record = {
            "protein_class_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["pref_name"] is None
        assert result["short_name"] is None
        assert result["protein_class_desc"] is None
        assert result["definition"] is None
        assert result["class_level"] is None
        assert result["sort_order"] is None
        assert result["replaced_by"] is None
        assert result["downgraded"] is None

    @pytest.mark.asyncio
    async def test_transform_with_string_protein_class_id(
        self, transformer, mock_context
    ):
        """Test that protein_class_id as string is converted to int."""
        record = {
            "protein_class_id": "100",
            "pref_name": "Kinase",
            "class_level": "2",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 100
        assert result["class_level"] == 2

    @pytest.mark.asyncio
    async def test_class_transformer__content_hash__b8ab6211(
        self, transformer, mock_context
    ):
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
    async def test_class_transformer__lineage_fields__c1f850bc(
        self, transformer, mock_context
    ):
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
        assert result["_source_batch_id"] is None
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_class_transformer__with_null_values__b3ce6491(
        self, transformer, mock_context
    ):
        """Test transformation handles None values correctly."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "pref_name": None,
            "short_name": None,
            "protein_class_desc": None,
            "definition": None,
            "class_level": None,
            "sort_order": None,
            "replaced_by": None,
            "downgraded": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["parent_id"] is None
        assert result["pref_name"] is None
        assert result["short_name"] is None
        assert result["protein_class_desc"] is None
        assert result["definition"] is None
        assert result["class_level"] is None
        assert result["sort_order"] is None
        assert result["replaced_by"] is None
        assert result["downgraded"] is None

    @pytest.mark.asyncio
    async def test_transform_deep_hierarchy_node(self, transformer, mock_context):
        """Test transformation of deep hierarchy node (level 8)."""
        record = {
            "protein_class_id": 8000,
            "parent_id": 7000,
            "pref_name": "Very Specific Subclass",
            "short_name": "VSS",
            "class_level": 8,
            "sort_order": 100,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["protein_class_id"] == 8000
        assert result["parent_id"] == 7000
        assert result["class_level"] == 8

    @pytest.mark.asyncio
    async def test_class_transformer__custom_provider__59d9be39(self, mock_context):
        """Test transformation with custom provider."""
        transformer = ProteinClassTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "protein_class_id": 1,
            "pref_name": "CustomClass",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result


@pytest.mark.unit
class TestProteinClassTransformerExtractBusinessData:
    """Tests for _extract_business_data method."""

    @pytest.fixture
    def transformer(self):
        """Create ProteinClassTransformer instance."""
        return ProteinClassTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    def test_extract_root_node(self, transformer):
        """Test extraction of root node data."""
        record = {
            "protein_class_id": 1,
            "parent_id": None,
            "pref_name": "Enzyme",
            "short_name": "Enzyme",
            "class_level": 1,
            "downgraded": 0,
        }

        result = transformer._extract_business_data(record, 1)

        assert result["protein_class_id"] == 1
        assert result["parent_id"] is None
        assert result["pref_name"] == "Enzyme"
        assert result["class_level"] == 1

    def test_extract_child_node(self, transformer):
        """Test extraction of child node data."""
        record = {
            "protein_class_id": 100,
            "parent_id": 1,
            "pref_name": "Kinase",
            "short_name": "Kinase",
            "class_level": 2,
            "protein_class_desc": "Enzymes that transfer phosphate groups",
            "definition": "Full kinase definition",
            "sort_order": 10,
            "replaced_by": None,
            "downgraded": 0,
        }

        result = transformer._extract_business_data(record, 100)

        assert result["protein_class_id"] == 100
        assert result["parent_id"] == 1
        assert result["class_level"] == 2
        assert result["sort_order"] == 10

    def test_extract_deprecated_node(self, transformer):
        """Test extraction of deprecated node data."""
        record = {
            "protein_class_id": 50,
            "parent_id": 1,
            "pref_name": "Old Classification",
            "class_level": 2,
            "replaced_by": 100,
            "downgraded": 1,
        }

        result = transformer._extract_business_data(record, 50)

        assert result["replaced_by"] == 100
        assert result["downgraded"] == 1
