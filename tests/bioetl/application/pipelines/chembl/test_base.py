"""Tests for ChemblPipelineBase."""

# pylint: disable=redefined-outer-name, unused-argument, protected-access
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry
from bioetl.domain.models import RunContext
from bioetl.domain.transform.contracts import HasherABC
from bioetl.infrastructure.transform.impl.chembl_normalization_service_impl import (
    ChemblNormalizationServiceImpl,
)
from bioetl.infrastructure.transform.impl.hash_service import Blake2bHashService


def _collect_extract_dataframe(pipeline: ChemblPipelineBase) -> pd.DataFrame:
    """Собирает все чанки extract в единый DataFrame для тестов."""
    extract_result = pipeline.extract()
    if isinstance(extract_result, pd.DataFrame):
        chunks = [extract_result]
    else:
        chunks = list(extract_result)
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


class ConcreteChemblPipeline(ChemblPipelineBase):
    """Concrete implementation for testing."""

    def extract(self, **_):
        """Mock extract implementation."""
        return pd.DataFrame()


@pytest.fixture
def mock_dependencies_fixture():
    """Fixture for pipeline dependencies."""

    class _DummyHasher(HasherABC):
        @property
        def algorithm(self) -> str:
            return "blake2b_256"

        def compute_hash(self, record):
            from bioetl.domain.value_objects import HashDigest

            return HashDigest("dummy_hash_row")

        def compute_hash_for_fields(self, record, fields):
            from bioetl.domain.value_objects import HashDigest

            return HashDigest("dummy_hash_business_key")

    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.id = "test_pipeline"
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    # Default schema columns
    validation_service.get_schema_columns.return_value = ["a", "transformed"]

    metadata_builder = MagicMock()
    metadata_builder.build_run_metadata.return_value = {}
    metadata_builder.build_dry_run_metadata.return_value = {}

    normalization_service = ChemblNormalizationServiceImpl(config=config)

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": validation_service,
        "loader": MagicMock(),
        "extraction_service": MagicMock(),
        "hash_service": Blake2bHashService(hasher=_DummyHasher()),
        "metadata_builder": metadata_builder,
        "normalization_service": normalization_service,
        "index_generator": MagicMock(),
        "timestamp_provider": MagicMock(),
    }


@pytest.fixture
def pipeline_fixture(mock_dependencies_fixture):
    """Fixture for pipeline instance."""
    mock_dependencies_fixture["config"].model_dump.return_value = {}

    # ExtractStage uses extraction_service.iter_extract instead of record_source
    mock_dependencies_fixture["extraction_service"].iter_extract.return_value = iter([])

    return ConcreteChemblPipeline(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        loader=mock_dependencies_fixture["loader"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        normalization_service=mock_dependencies_fixture["normalization_service"],
        hash_service=mock_dependencies_fixture["hash_service"],
        metadata_builder=mock_dependencies_fixture["metadata_builder"],
        index_generator=mock_dependencies_fixture["index_generator"],
        timestamp_provider=mock_dependencies_fixture["timestamp_provider"],
        entity_model_registry=get_chembl_model_registry(),
    )


def test_get_chembl_release(pipeline_fixture, mock_dependencies_fixture, monkeypatch):
    """Test ChEMBL release version retrieval.

    ExtractionService returns raw version ('34'), application layer
    formats it using domain service to 'chembl_34'.
    """
    # ExtractionService now returns raw version without prefix
    mock_dependencies_fixture["extraction_service"].get_release_version.return_value = (
        "34"
    )
    monkeypatch.setattr(
        pipeline_fixture, "_should_skip_release_lookup", lambda: False, raising=False
    )

    release1 = pipeline_fixture.get_chembl_release()
    release2 = pipeline_fixture.get_chembl_release()

    # Application layer formats to 'chembl_34'
    assert release1 == "chembl_34"
    assert release2 == "chembl_34"
    (
        mock_dependencies_fixture[
            "extraction_service"
        ].get_release_version.assert_called_once()
    )


def test_enrich_context(pipeline_fixture, mock_dependencies_fixture, monkeypatch):
    """Test context enrichment with ChEMBL release.

    ExtractionService returns raw version ('99'), application layer
    formats it and stores as 'chembl_99' in context metadata.
    """
    # ExtractionService now returns raw version without prefix
    mock_dependencies_fixture["extraction_service"].get_release_version.return_value = (
        "99"
    )
    monkeypatch.setattr(
        pipeline_fixture, "_should_skip_release_lookup", lambda: False, raising=False
    )
    context = RunContext(
        entity_name="test", provider="chembl", started_at=datetime.now(timezone.utc)
    )

    pipeline_fixture._enrich_context(context)

    assert "chembl_release" in context.metadata
    # Formatted in application layer
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
    # Explicitly set serialization mode to pipe to match expected output
    mock_dependencies_fixture["config"].serialization_mode = "pipe"
    # Also update the already initialized service
    service = mock_dependencies_fixture["normalization_service"]
    if hasattr(service, "_base"):
        service._base._serialization_mode = "pipe"
    else:
        service._serialization_mode = "pipe"

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
    normalized_df = pd.DataFrame({"a": [1, 2], "transformed": [True, True]})
    normalization_service.normalize.return_value = normalized_df

    # ExtractStage uses extraction_service.iter_extract instead of record_source
    mock_dependencies_fixture["extraction_service"].iter_extract.return_value = iter([])

    pipeline = ConcreteChemblPipeline(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        loader=mock_dependencies_fixture["loader"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        normalization_service=normalization_service,
        hash_service=mock_dependencies_fixture["hash_service"],
        metadata_builder=mock_dependencies_fixture["metadata_builder"],
        index_generator=mock_dependencies_fixture["index_generator"],
        timestamp_provider=mock_dependencies_fixture["timestamp_provider"],
        entity_model_registry=get_chembl_model_registry(),
    )

    df = pd.DataFrame({"a": [1, 2]})

    result = pipeline.transform(df)

    normalization_service.normalize.assert_called_once()

    # Verify result was normalized (may be modified by transformer)
    assert isinstance(result, pd.DataFrame)


def test_extract_handles_dataframe_chunks(mock_dependencies_fixture):
    """Test that extract yields DataFrame chunks for further processing.

    ExtractStage uses extraction_service.iter_extract() and yields
    DataFrames. Normalization is now done in the transformer stage,
    not during extraction.

    Note: We must use a valid ChEMBL entity (activity) because ExtractStage
    uses ChemblRecordMapper which validates records against domain models.
    """
    # Use activity records that match ActivityRawModel requirements
    raw_chunks = [
        [
            {"activity_id": 1, "standard_flag": True, "standard_value": 1.0},
            {"activity_id": 2, "standard_flag": True, "standard_value": 2.0},
        ],
        [{"activity_id": 3, "standard_flag": False}],
    ]
    # ExtractStage uses extraction_service.iter_extract
    mock_dependencies_fixture["extraction_service"].iter_extract.return_value = iter(
        raw_chunks
    )

    # Update config to use 'activity' entity
    mock_dependencies_fixture["config"].entity_name = "activity"

    normalization_service = MagicMock()
    normalization_service.normalize.return_value = pd.DataFrame({"a": [1]})

    pipeline = ChemblPipelineBase(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        loader=mock_dependencies_fixture["loader"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
        normalization_service=normalization_service,
        hash_service=mock_dependencies_fixture["hash_service"],
        metadata_builder=mock_dependencies_fixture["metadata_builder"],
        index_generator=mock_dependencies_fixture["index_generator"],
        timestamp_provider=mock_dependencies_fixture["timestamp_provider"],
        entity_model_registry=get_chembl_model_registry(),
    )

    result = _collect_extract_dataframe(pipeline)

    # ExtractStage yields raw DataFrames without normalization
    # Normalization is now done in the transformer stage
    assert normalization_service.normalize.call_count == 0

    # ChemblRecordMapper converts records to full domain models with all fields
    # We verify the key columns have correct values
    assert len(result) == 3
    assert "activity_id" in result.columns
    assert "standard_flag" in result.columns
    # ChemblRecordMapper converts activity_id to string
    assert result["activity_id"].tolist() == ["1", "2", "3"]
    assert result["standard_flag"].tolist() == [True, True, False]
