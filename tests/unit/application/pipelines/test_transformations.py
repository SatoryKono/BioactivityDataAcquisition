"""Unit tests for the transformation logic in pipelines."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


# Mock context object for tests
@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a real PipelineContext with mock logger.

    Using real PipelineContext instead of MagicMock because transformers
    now use context.run_id and context.run_type for entity creation.
    """
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


# Mock pipeline base for instantiation
@pytest.fixture
def mock_pipeline_base():
    mock = MagicMock()
    mock.provider = "test_provider"
    return mock


@pytest.fixture
def mock_run_id() -> RunID:
    """Create a test run ID."""
    return uuid4()


class TestPubChemCompoundPipeline:
    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_success(
        self, mock_context, mock_pipeline_base, mock_run_id
    ):
        # Arrange
        config = MagicMock()
        config.provider = "pubchem"
        transformer = PubChemCompoundTransformer(provider="pubchem")
        pipeline = PubChemCompoundPipeline(
            config=config, runtime=MagicMock(), services=MagicMock(), run_id=mock_run_id, transformer=transformer
        )

        record = {
            "cid": 123,
            "molecular_formula": "C6H6",
            "molecular_weight": "78.11",
            "canonical_smiles": "c1ccccc1",
        }

        # Act
        result = await pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is not None
        assert result["cid"] == "123"
        assert result["molecular_formula"] == "C6H6"
        assert "entity_id" in result
        assert "content_hash" in result
        assert result["entity_id"] is not None
        assert result["content_hash"] is not None
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_no_cid(
        self, mock_context, mock_pipeline_base, mock_run_id
    ):
        # Arrange
        transformer = PubChemCompoundTransformer(provider="pubchem")
        pipeline = PubChemCompoundPipeline(
            config=MagicMock(),
            runtime=MagicMock(),
            services=MagicMock(),
            run_id=mock_run_id,
            transformer=transformer,
        )
        record = {"molecular_formula": "C6H6"}

        # Act
        result = await pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is None


class TestUniProtProteinPipeline:
    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_success(
        self, mock_context, mock_pipeline_base, mock_run_id
    ):
        # Arrange
        config = MagicMock()
        config.provider = "uniprot"
        transformer = UniProtProteinTransformer(provider="uniprot")
        pipeline = UniProtProteinPipeline(
            config=config,
            runtime=MagicMock(),
            services=MagicMock(),
            run_id=mock_run_id,
            transformer=transformer,
        )

        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_ID",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Test Protein"}}
            },
            "genes": [{"geneName": {"value": "TP1"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 100},
        }

        # Act
        result = await pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is not None
        assert result["accession"] == "P12345"
        assert result["protein_name"] == "Test Protein"
        assert "entity_id" in result
        assert "content_hash" in result
        assert result["entity_id"] is not None
        assert result["content_hash"] is not None
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_no_accession(
        self, mock_context, mock_pipeline_base, mock_run_id
    ):
        # Arrange
        transformer = UniProtProteinTransformer(provider="uniprot")
        pipeline = UniProtProteinPipeline(
            config=MagicMock(),
            runtime=MagicMock(),
            services=MagicMock(),
            run_id=mock_run_id,
            transformer=transformer,
        )
        record = {"uniProtkbId": "TEST_ID"}

        # Act
        result = await pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is None
