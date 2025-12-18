"""Unit tests for the transformation logic in pipelines."""

import pytest
from unittest.mock import MagicMock

from bioetl.application.pipelines.pubchem_compound import PubChemCompoundPipeline
from bioetl.application.pipelines.uniprot_protein import UniProtProteinPipeline
from bioetl.domain.context import PipelineContext

# Mock context object for tests
@pytest.fixture
def mock_context() -> PipelineContext:
    return MagicMock(spec=PipelineContext)

# Mock pipeline base for instantiation
@pytest.fixture
def mock_pipeline_base():
    mock = MagicMock()
    mock.provider = "test_provider"
    return mock

class TestPubChemCompoundPipeline:
    def test_transform_bronze_to_silver_success(self, mock_context, mock_pipeline_base):
        # Arrange
        pipeline = PubChemCompoundPipeline(config=MagicMock(), runtime=MagicMock(), services=MagicMock())
        pipeline.provider = "pubchem"  # Set provider for hash generation

        record = {
            "cid": 123,
            "molecular_formula": "C6H6",
            "molecular_weight": "78.11",
            "canonical_smiles": "c1ccccc1",
        }

        # Act
        result = pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is not None
        assert result["cid"] == "123"
        assert result["molecular_formula"] == "C6H6"
        assert "entity_id" in result
        assert "content_hash" in result
        assert result["entity_id"] is not None
        assert result["content_hash"] is not None

    def test_transform_bronze_to_silver_no_cid(self, mock_context, mock_pipeline_base):
        # Arrange
        pipeline = PubChemCompoundPipeline(config=MagicMock(), runtime=MagicMock(), services=MagicMock())
        record = {"molecular_formula": "C6H6"}

        # Act
        result = pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is None

class TestUniProtProteinPipeline:
    def test_transform_bronze_to_silver_success(self, mock_context, mock_pipeline_base):
        # Arrange
        pipeline = UniProtProteinPipeline(config=MagicMock(), runtime=MagicMock(), services=MagicMock())
        pipeline.provider = "uniprot" # Set provider for hash generation

        record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "TEST_ID",
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Test Protein"}}},
            "genes": [{"geneName": {"value": "TP1"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 100},
        }

        # Act
        result = pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is not None
        assert result["accession"] == "P12345"
        assert result["protein_name"] == "Test Protein"
        assert "entity_id" in result
        assert "content_hash" in result
        assert result["entity_id"] is not None
        assert result["content_hash"] is not None

    def test_transform_bronze_to_silver_no_accession(self, mock_context, mock_pipeline_base):
        # Arrange
        pipeline = UniProtProteinPipeline(config=MagicMock(), runtime=MagicMock(), services=MagicMock())
        record = {"uniProtkbId": "TEST_ID"}

        # Act
        result = pipeline.transform_bronze_to_silver(mock_context, record)

        # Assert
        assert result is None
