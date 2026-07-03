"""Unit tests for ChEMBL Cell Line Transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
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
        run_id=deterministic_uuid_from_callsite("test_cell_line_transformer"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestCellLineTransformer:
    """Tests for CellLineTransformer."""

    @pytest.fixture
    def transformer(self):
        """Create CellLineTransformer instance."""
        return CellLineTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.mark.asyncio
    async def test_transform_valid_record(self, transformer, mock_context):
        """Test transformation of valid cell line record."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_description": "Human cervical cancer cell line",
            "cell_source_tissue": "Cervix",
            "cell_source_organism": "Homo sapiens",
            "cell_source_tax_id": 9606,  # Source API field name
            "cell_type": "Cancer cell line",
            "cellosaurus_id": "CVCL_0030",
            "clo_id": "CLO_0003684",
            "cl_lincs_id": "LCL-1234",
            "efo_id": "EFO_0001185",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_id"] == "CHEMBL3308376"
        assert result["cell_name"] == "HeLa"
        assert result["cell_description"] == "Human cervical cancer cell line"
        assert result["cell_source_tissue"] == "Cervix"
        assert result["cell_source_organism"] == "Homo sapiens"
        assert result["cell_source_taxonomy_id"] == 9606
        assert result["cell_type"] == "Cancer cell line"
        assert result["cellosaurus_id"] == "CVCL_0030"
        assert result["clo_id"] == "CLO_0003684"
        assert result["cl_lincs_id"] == "LCL-1234"
        assert result["efo_id"] == "EFO_0001185"
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_cell_id(self, transformer, mock_context):
        """Test transformation returns None when cell_id is missing."""
        record = {
            "cell_name": "HeLa",
            "cell_source_organism": "Homo sapiens",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_minimal_record(self, transformer, mock_context):
        """Test transformation with only required fields."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_id"] == "CHEMBL3308376"
        assert result["cell_name"] == "HeLa"
        assert result["cell_description"] is None
        assert result["cell_source_tissue"] is None
        assert result["cell_source_organism"] is None
        assert result["cell_source_taxonomy_id"] is None
        assert result["cell_type"] is None
        assert result["cellosaurus_id"] is None
        assert result["clo_id"] is None
        assert result["cl_lincs_id"] is None
        assert result["efo_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_whitespace_in_cell_name(
        self, transformer, mock_context
    ):
        """Test that cell_name is stripped of leading/trailing whitespace."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "  HeLa  ",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_name"] == "HeLa"

    @pytest.mark.asyncio
    async def test_transform_with_empty_external_ids(self, transformer, mock_context):
        """Test that empty string external IDs become None."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cellosaurus_id": "",
            "clo_id": "   ",
            "cl_lincs_id": "   ",
            "efo_id": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cellosaurus_id"] is None
        assert result["clo_id"] is None
        assert result["cl_lincs_id"] is None
        assert result["efo_id"] is None

    @pytest.mark.asyncio
    async def test_transform_strips_external_id_whitespace(
        self, transformer, mock_context
    ):
        """Test that external IDs are stripped of whitespace."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cellosaurus_id": "  CVCL_0030  ",
            "clo_id": "\tCLO_0003684\n",
            "cl_lincs_id": "\tLCL-1234\n",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cellosaurus_id"] == "CVCL_0030"
        assert result["clo_id"] == "CLO_0003684"
        assert result["cl_lincs_id"] == "LCL-1234"

    @pytest.mark.asyncio
    async def test_transform_with_invalid_tax_id_zero(self, transformer, mock_context):
        """Test that taxonomy_id of 0 becomes None (must be >= 1)."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_source_tax_id": 0,  # Source API field name
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_source_taxonomy_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_negative_tax_id(self, transformer, mock_context):
        """Test that negative taxonomy_id becomes None (must be >= 1)."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_source_tax_id": -1,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_source_taxonomy_id"] is None

    @pytest.mark.asyncio
    async def test_transform_with_valid_tax_id(self, transformer, mock_context):
        """Test that valid taxonomy_id is preserved."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_source_tax_id": 9606,  # Source API field name
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_source_taxonomy_id"] == 9606

    @pytest.mark.asyncio
    async def test_transform_with_tax_id_as_string(self, transformer, mock_context):
        """Test that taxonomy_id as string is converted to int."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_source_tax_id": "9606",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_source_taxonomy_id"] == 9606

    @pytest.mark.asyncio
    async def test_cell_line_transformer__custom_provider__1fa53ba3(self, mock_context):
        """Test transformation with custom provider."""
        transformer = CellLineTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "cell_id": "CUSTOM123",
            "cell_name": "CustomCell",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result

    @pytest.mark.asyncio
    async def test_transform_generates_content_hash(self, transformer, mock_context):
        """Test that content_hash is generated and is 64 hex characters."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
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
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
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
    async def test_transform_api_record_with_numeric_cell_id(
        self, transformer, mock_context
    ):
        """Test that numeric cell_id from API is replaced with cell_chembl_id.

        ChEMBL /cell_line API returns both cell_id (numeric, e.g. 449)
        and cell_chembl_id (e.g. CHEMBL3308072). The transformer must
        use cell_chembl_id as the canonical cell_id for Silver.
        """
        record = {
            "cell_chembl_id": "CHEMBL3308072",
            "cell_id": 449,
            "cell_name": "CHO",
            "cell_description": "Ovarian cells",
            "cell_source_organism": "Cricetulus griseus",
            "cell_source_tax_id": 10029,
            "cell_source_tissue": "Ovarian cells",
            "cellosaurus_id": "CVCL_0213",
            "clo_id": "CLO_0002421",
            "cl_lincs_id": None,
            "efo_id": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_id"] == "CHEMBL3308072"

    @pytest.mark.asyncio
    async def test_transform_only_cell_chembl_id(self, transformer, mock_context):
        """Test fallback when only cell_chembl_id is present (no cell_id)."""
        record = {
            "cell_chembl_id": "CHEMBL3308072",
            "cell_name": "CHO",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_id"] == "CHEMBL3308072"

    @pytest.mark.asyncio
    async def test_transform_with_null_values(self, transformer, mock_context):
        """Test transformation handles None values correctly."""
        record = {
            "cell_id": "CHEMBL3308376",
            "cell_name": "HeLa",
            "cell_description": None,
            "cell_source_tissue": None,
            "cell_source_organism": None,
            "cell_source_tax_id": None,
            "cell_type": None,
            "cellosaurus_id": None,
            "clo_id": None,
            "cl_lincs_id": None,
            "efo_id": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["cell_description"] is None
        assert result["cell_source_tissue"] is None
        assert result["cell_source_organism"] is None
        assert result["cell_source_taxonomy_id"] is None
        assert result["cell_type"] is None
        assert result["cellosaurus_id"] is None
        assert result["clo_id"] is None
        assert result["cl_lincs_id"] is None
        assert result["efo_id"] is None
