"""Tests for ChemblPipelineBase."""
# pylint: disable=redefined-outer-name, unused-argument
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.domain.models import RunContext
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.infrastructure.ingestion import NormalizationIngestionService


class ConcreteChemblPipeline(ChemblPipelineBase):
    """Concrete implementation for testing."""

    def extract(self, **_):
        """Mock extract implementation."""
        return pd.DataFrame()

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df["transformed"] = True
        return df


@pytest.fixture
def mock_dependencies_fixture():
    """Fixture for pipeline dependencies."""
    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []

    validation_service = MagicMock()
    validation_service.get_schema_columns.return_value = ["a", "transformed"]

    normalization_service = NormalizationService(config)
    ingestion_service = NormalizationIngestionService(
        normalization_service=normalization_service,
        validation_service=validation_service,
        logger=MagicMock(),
    )

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": validation_service,
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
        "ingestion_service": ingestion_service,
    }


@pytest.fixture
def pipeline_fixture(mock_dependencies_fixture):
    """Fixture for pipeline instance."""
    mock_dependencies_fixture["config"].model_dump.return_value = {}

    return ConcreteChemblPipeline(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        output_writer=mock_dependencies_fixture["output_writer"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        ingestion_service=mock_dependencies_fixture["ingestion_service"],
    )


def test_get_chembl_release(pipeline_fixture, mock_dependencies_fixture):
    """Test ChEMBL release version retrieval."""
    mock_dependencies_fixture[
        "extraction_service"
    ].get_release_version.return_value = "chembl_34"

    release1 = pipeline_fixture.get_chembl_release()
    release2 = pipeline_fixture.get_chembl_release()

    assert release1 == "chembl_34"
    assert release2 == "chembl_34"
    (
        mock_dependencies_fixture["extraction_service"]
        .get_release_version.assert_called_once()
    )


def test_pre_transform_hook(pipeline_fixture):
    """Test pre_transform hook."""
    df = pd.DataFrame({"a": [1]})
    result = pipeline_fixture.pre_transform(df)
    pd.testing.assert_frame_equal(df, result)


def test_enrich_context(pipeline_fixture, mock_dependencies_fixture):
    """Test context enrichment with ChEMBL release."""
    mock_dependencies_fixture[
        "extraction_service"
    ].get_release_version.return_value = "chembl_99"
    context = RunContext(
        entity_name="test",
        provider="chembl",
        started_at=datetime.now(timezone.utc)
    )

    pipeline_fixture._enrich_context(context)

    assert "chembl_release" in context.metadata
    assert context.metadata["chembl_release"] == "chembl_99"


def test_transform_nested_normalization(
    pipeline_fixture, mock_dependencies_fixture
):
    """Test that transform applies nested normalization."""
    mock_dependencies_fixture["config"].fields = [
        {"name": "nested", "data_type": "array"},
        {"name": "obj", "data_type": "object"},
        {"name": "simple", "data_type": "string"},
        {"name": "pubmed_id", "data_type": "string"},
        {"name": "references", "data_type": "array"},
        {"name": "doi", "data_type": "string"},
    ]
    norm = MagicMock()
    norm.case_sensitive_fields = []
    norm.id_fields = []
    mock_dependencies_fixture["config"].normalization = norm

    schema_cols = [
        "nested", "obj", "simple", "pubmed_id",
        "references", "doi", "transformed"
    ]
    validation = pipeline_fixture._validation_service
    validation.get_schema_columns.return_value = schema_cols

    df = pd.DataFrame({
        "nested": [["x", "y"], ["z"]],
        "obj": [{"k": "v"}, None],
        "simple": ["s1", "s2"],
        "pubmed_id": [" 12345 ", "67890"],
        "references": [["12345", 67890], [None, " 333 "]],
        "doi": ["https://doi.org/10.1000/ABC", "10.2345/xyz"]
    })

    result = pipeline_fixture.transform(df)

    assert "transformed" in result.columns
    assert result.iloc[0]["nested"] == "x|y"
    assert result.iloc[0]["obj"] == "k:v"
    assert result.iloc[1]["nested"] == "z"
    assert pd.isna(result.iloc[1]["obj"])
    assert result.iloc[0]["simple"] == "s1"
    assert result.iloc[0]["pubmed_id"] == 12345
    assert result.iloc[0]["references"] == "12345|67890"
    assert result.iloc[1]["references"] == "333"
    assert result.iloc[0]["doi"] == "10.1000/abc"
