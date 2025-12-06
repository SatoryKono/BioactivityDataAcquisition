"""Tests for ChemblPipelineBase."""

# pylint: disable=redefined-outer-name, unused-argument, protected-access
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService


class ConcreteChemblPipeline(ChemblPipelineBase):
    """Concrete implementation for testing."""

    def extract(self, **_):
        """Mock extract implementation."""
        return pd.DataFrame()


@pytest.fixture
def mock_dependencies_fixture():
    """Fixture for pipeline dependencies."""
    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.id = "test_pipeline"
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []

    validation_service = MagicMock()
    # Default schema columns
    validation_service.get_schema_columns.return_value = ["a", "transformed"]

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": validation_service,
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
        "hash_service": HashService(),
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
        hash_service=mock_dependencies_fixture["hash_service"],
    )


def test_get_chembl_release(pipeline_fixture, mock_dependencies_fixture):
    """Test ChEMBL release version retrieval."""
    mock_dependencies_fixture["extraction_service"].get_release_version.return_value = (
        "chembl_34"
    )

    release1 = pipeline_fixture.get_chembl_release()
    release2 = pipeline_fixture.get_chembl_release()

    assert release1 == "chembl_34"
    assert release2 == "chembl_34"
    (
        mock_dependencies_fixture[
            "extraction_service"
        ].get_release_version.assert_called_once()
    )


def test_enrich_context(pipeline_fixture, mock_dependencies_fixture):
    """Test context enrichment with ChEMBL release."""
    mock_dependencies_fixture["extraction_service"].get_release_version.return_value = (
        "chembl_99"
    )
    context = RunContext(
        entity_name="test", provider="chembl", started_at=datetime.now(timezone.utc)
    )

    pipeline_fixture._enrich_context(context)

    assert "chembl_release" in context.metadata
    assert context.metadata["chembl_release"] == "chembl_99"


def test_transform_nested_normalization(pipeline_fixture, mock_dependencies_fixture):
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

    schema_cols = ["nested", "obj", "simple", "pubmed_id", "references", "doi"]
    validation = pipeline_fixture._validation_service
    validation.get_schema_columns.return_value = schema_cols

    df = pd.DataFrame(
        {
            "nested": [["x", "y"], ["z"]],
            "obj": [{"k": "v"}, None],
            "simple": ["s1", "s2"],
            "pubmed_id": [" 12345 ", "67890"],
            "references": [["12345", 67890], [None, " 333 "]],
            "doi": ["https://doi.org/10.1000/ABC", "10.2345/xyz"],
        }
    )

    result = pipeline_fixture.transform(df)

    _assert_normalized_columns(result, schema_cols)
    _assert_normalized_row(
        result,
        0,
        {
            "nested": "x|y",
            "obj": "k:v",
            "simple": "s1",
            "pubmed_id": 12345,
            "references": "12345|67890",
            "doi": "10.1000/abc",
        },
    )
    _assert_normalized_row(
        result,
        1,
        {
            "nested": "z",
            "obj": None,
            "simple": "s2",
            "pubmed_id": 67890,
            "references": "333",
            "doi": "10.2345/xyz",
        },
    )


def _assert_normalized_columns(result: pd.DataFrame, expected: list[str]) -> None:
    assert list(result.columns) == expected


def _assert_normalized_row(
    result: pd.DataFrame, index: int, expected: dict[str, object]
) -> None:
    row = result.iloc[index]
    for key, expected_value in expected.items():
        actual = row[key]
        if expected_value is None and pd.isna(actual):
            continue
        assert actual == expected_value


def test_transform_uses_batch_normalization(mock_dependencies_fixture):
    """Ensure transform delegates batch normalization to the service."""
    normalization_service = MagicMock()
    normalization_service.normalize_dataframe.return_value = pd.DataFrame(
        {"a": [1, 2], "transformed": [True, True]}
    )

    pipeline = ConcreteChemblPipeline(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        output_writer=mock_dependencies_fixture["output_writer"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        normalization_service=normalization_service,
        hash_service=mock_dependencies_fixture["hash_service"],
    )

    df = pd.DataFrame({"a": [1, 2]})

    result = pipeline.transform(df)

    normalization_service.normalize_dataframe.assert_called_once()

    # Verify result matches normalization output
    pd.testing.assert_frame_equal(
        result, normalization_service.normalize_dataframe.return_value
    )


def test_extract_handles_dataframe_chunks(mock_dependencies_fixture):
    """Test that extract yields DataFrame chunks for further processing."""
    record_source = MagicMock()
    raw_chunks = [
        pd.DataFrame([{"id": 1}, {"id": 2}]),
        pd.DataFrame([{"id": 3}]),
    ]
    record_source.iter_records.return_value = raw_chunks

    normalization_service = MagicMock()
    normalization_service.normalize_batch.side_effect = lambda df: df.assign(
        processed=True
    )

    pipeline = ChemblPipelineBase(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        output_writer=mock_dependencies_fixture["output_writer"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        record_source=record_source,
        normalization_service=normalization_service,
        hash_service=mock_dependencies_fixture["hash_service"],
    )

    result = pipeline.extract()

    assert normalization_service.normalize_batch.call_count == 2

    expected = pd.concat(
        [chunk.assign(processed=True) for chunk in raw_chunks], ignore_index=True
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected.reset_index(drop=True)
    )
