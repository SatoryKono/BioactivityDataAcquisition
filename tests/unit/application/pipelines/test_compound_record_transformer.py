"""Unit tests for ChEMBL Compound Record Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
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
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestCompoundRecordTransformer:
    """Tests for CompoundRecordTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create CompoundRecordTransformer instance."""
        return CompoundRecordTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_record_transformer__valid_record__de53ac02(self, transformer, mock_context):
        """Test transformation of valid compound record."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "compound_key": "Aspirin",
            "compound_name": "Acetylsalicylic amolecule_id",
            "src_id": 1,
            "src_compound_id": "ASPIRIN-001",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["record_id"] == 12345
        assert result["molecule_id"] == "CHEMBL25"
        assert result["publication_id"] == "CHEMBL1123456"
        assert result["compound_key"] == "Aspirin"
        assert result["compound_name"] == "Acetylsalicylic amolecule_id"
        assert result["src_id"] == 1
        assert result["src_compound_id"] == "ASPIRIN-001"
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_record_id(self, transformer, mock_context):
        """Test transformation returns None when record_id is missing."""
        record = {
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_record_transformer__minimal_record__37ea52d0(self, transformer, mock_context):
        """Test transformation with only required fields."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["record_id"] == 12345
        assert result["molecule_id"] == "CHEMBL25"
        assert result["publication_id"] == "CHEMBL1123456"
        assert result["src_id"] == 1
        assert result["compound_key"] is None
        assert result["compound_name"] is None
        assert result["src_compound_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_whitespace_in_compound_key(
        self, transformer, mock_context
    ):
        """Test that compound_key is stripped of leading/trailing whitespace."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "  Aspirin  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["compound_key"] == "Aspirin"

    @pytest.mark.asyncio
    async def test_transform_with_whitespace_in_compound_name(
        self, transformer, mock_context
    ):
        """Test that compound_name is stripped of leading/trailing whitespace."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_name": "\tAcetylsalicylic amolecule_id\n",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["compound_name"] == "Acetylsalicylic amolecule_id"

    @pytest.mark.asyncio
    async def test_transform_with_empty_strings(self, transformer, mock_context):
        """Test that empty string fields become None."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "",
            "compound_name": "   ",
            "src_compound_id": "",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["compound_key"] is None
        assert result["compound_name"] is None
        assert result["src_compound_id"] is None

    @pytest.mark.asyncio
    async def test_record_transformer__with_null_values__2265c6dd(self, transformer, mock_context):
        """Test transformation handles None values correctly."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": None,
            "compound_name": None,
            "src_compound_id": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["compound_key"] is None
        assert result["compound_name"] is None
        assert result["src_compound_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_record_id_as_string(self, transformer, mock_context):
        """Test that record_id as string is converted to int."""
        record = {
            "record_id": "12345",
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": "1",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["record_id"] == 12345
        assert result["src_id"] == 1

    @pytest.mark.asyncio
    async def test_record_transformer__custom_provider__f1ba3a38(self, mock_context):
        """Test transformation with custom provider."""
        transformer = CompoundRecordTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "record_id": 12345,
            "molecule_id": "CUSTOM25",
            "publication_id": "CUSTOM1123456",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result

    @pytest.mark.asyncio
    async def test_record_transformer__content_hash__9c99529a(self, transformer, mock_context):
        """Test that content_hash is generated and is 64 hex characters."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64
        # Verify it's a valid hex string
        int(result["content_hash"], 16)

    @pytest.mark.asyncio
    async def test_record_transformer__lineage_fields__17d8ebe0(self, transformer, mock_context):
        """Test that all lineage fields are present."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
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
    async def test_transform_strips_src_compound_id(self, transformer, mock_context):
        """Test that src_compound_id is stripped of whitespace."""
        record = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "src_compound_id": "  ASPIRIN-001  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["src_compound_id"] == "ASPIRIN-001"

    @pytest.mark.asyncio
    async def test_transform_same_records_produce_same_hash(
        self, transformer, mock_context
    ):
        """Test that identical records produce the same content hash."""
        record1 = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "Aspirin",
        }
        record2 = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "Aspirin",
        }

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=1)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] == result2["content_hash"]

    @pytest.mark.asyncio
    async def test_transform_different_records_produce_different_hash(
        self, transformer, mock_context
    ):
        """Test that different records produce different content hashes."""
        record1 = {
            "record_id": 12345,
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "Aspirin",
        }
        record2 = {
            "record_id": 12346,  # Different record_id
            "molecule_id": "CHEMBL25",
            "publication_id": "CHEMBL1123456",
            "src_id": 1,
            "compound_key": "Aspirin",
        }

        result1 = await transformer.transform(mock_context, record1, index=0)
        result2 = await transformer.transform(mock_context, record2, index=1)

        assert result1 is not None
        assert result2 is not None
        assert result1["content_hash"] != result2["content_hash"]
