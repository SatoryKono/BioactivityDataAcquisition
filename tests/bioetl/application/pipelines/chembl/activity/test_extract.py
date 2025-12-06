"""
Tests for ChemblPipelineBase generic extract (via ChemblActivityPipeline).
"""

from typing import cast
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.pipeline import (
    ChemblEntityPipeline,
)
from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    CsvInputOptions,
)
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)


@pytest.fixture
def source_config():
    """Create test ChemblSourceConfig with flat structure."""
    return ChemblSourceConfig(
        base_url="https://test.com",
        batch_size=100,
        timeout_sec=30,
        max_retries=3,
        rate_limit_per_sec=5.0,
    )


@pytest.fixture
def mock_config(source_config):
    """Create mock PipelineConfig with get_source_config method."""
    config = MagicMock()
    config.id = "chembl.activity"
    config.pipeline = {}
    config.entity_name = "activity"
    config.provider = "chembl"
    config.provider_config = source_config
    config.get_source_config = lambda provider: config.provider_config
    config.normalization = MagicMock()
    config.normalization.rules = {}
    config.hashing = MagicMock()
    config.hashing.business_key_fields = ["activity_id"]
    config.primary_key = "activity_id"
    config.input_mode = "auto_detect"
    config.input_path = None
    config.csv_options = CsvInputOptions()
    config.model_dump.return_value = {}
    return config


@pytest.fixture
def mock_extraction_service():
    service = MagicMock()
    service.extract_all.return_value = pd.DataFrame({"activity_id": [1, 2, 3]})
    service.iter_extract.return_value = iter([pd.DataFrame({"activity_id": [1, 2, 3]})])
    service.request_batch.return_value = {"activities": [{"activity_id": 1}]}
    return service


@pytest.fixture
def mock_normalization_service():
    """Create mock normalization service."""
    service = MagicMock()
    service.normalize_batch.side_effect = lambda df: df
    service.normalize_dataframe.side_effect = lambda df: df
    return service


@pytest.fixture
def pipeline(mock_config, mock_extraction_service, mock_normalization_service):
    """Create pipeline with mocked dependencies."""
    logger = MagicMock()
    validation_service = MagicMock()
    output_writer = MagicMock()

    return ChemblEntityPipeline(
        config=mock_config,
        logger=logger,
        validation_service=validation_service,
        output_writer=output_writer,
        extraction_service=mock_extraction_service,
        hash_service=MagicMock(),
        normalization_service=mock_normalization_service,
    )


def test_extract_no_input_file(pipeline, mock_extraction_service):
    """Test extraction falls back to service when no input file."""
    pipeline._config.input_mode = "auto_detect"
    pipeline._config.input_path = None

    df = pipeline.extract()

    mock_extraction_service.iter_extract.assert_called_once()
    assert not df.empty
    assert "activity_id" in df.columns


def test_extract_full_data_csv(pipeline, mock_extraction_service, tmp_path):
    """Test extraction reads full dataframe from CSV."""
    csv_path = tmp_path / "activity.csv"
    pd.DataFrame(
        {
            "activity_id": [10, 11],
            "standard_value": [5.5, 6.6],
            "standard_type": ["IC50", "Ki"],
        }
    ).to_csv(csv_path, index=False)

    pipeline._config.input_mode = "csv"
    pipeline._config.input_path = str(csv_path)

    # Create CsvRecordSourceImpl and replace it in extractor
    csv_record_source = CsvRecordSourceImpl(
        input_path=csv_path,
        csv_options=pipeline._config.csv_options,
        limit=None,
        logger=cast(LoggerAdapterABC, MagicMock()),
    )
    pipeline._extractor.record_source = csv_record_source

    df = pipeline.extract()

    assert len(df) == 2
    assert "standard_value" in df.columns
    mock_extraction_service.extract_all.assert_not_called()
    mock_extraction_service.iter_extract.assert_not_called()
    mock_extraction_service.request_batch.assert_not_called()


def test_extract_ids_only_csv(
    pipeline, mock_extraction_service, tmp_path, source_config
) -> None:
    """Test extraction fetches data by IDs when CSV contains only IDs."""
    csv_path = tmp_path / "activity_ids.csv"
    ids_df = pd.DataFrame({"activity_id": [100, 101, 102]})
    ids_df.to_csv(csv_path, index=False)

    pipeline._config.input_mode = "id_only"
    pipeline._config.input_path = str(csv_path)

    # Create IdListRecordSourceImpl and replace it in extractor
    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggerAdapterABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    # Mock parse_response to return records only once
    # One batch covers all ids (batch_size=25 > 3), parse called once
    mock_extraction_service.parse_response.return_value = [
        {"activity_id": 100},
        {"activity_id": 101},
        {"activity_id": 102},
    ]

    # Mock serialize_records to return input
    mock_extraction_service.serialize_records.side_effect = lambda entity, recs: recs

    df = pipeline.extract()

    assert len(df) == 3
    mock_extraction_service.request_batch.assert_called()
    call_args = mock_extraction_service.request_batch.call_args
    # request_batch(entity, batch_ids, filter_key)
    assert call_args[0][0] == "activity"
    assert "100" in call_args[0][1]


def test_extract_batch_size_from_config(
    pipeline, mock_extraction_service, tmp_path, source_config
):
    """Test that batch_size from config controls chunking."""
    csv_path = tmp_path / "activity_batch_test.csv"
    ids = [1, 2, 3, 4, 5]
    pd.DataFrame({"activity_id": ids}).to_csv(csv_path, index=False)

    pipeline._config.input_mode = "id_only"
    pipeline._config.input_path = str(csv_path)
    # Create new source_config with batch_size=2
    from bioetl.infrastructure.config.models import ChemblSourceConfig

    new_source_config = ChemblSourceConfig(
        base_url=source_config.base_url,
        batch_size=2,
        timeout_sec=source_config.timeout_sec,
        max_retries=source_config.max_retries,
        rate_limit_per_sec=source_config.rate_limit_per_sec,
    )
    pipeline._config.provider_config = new_source_config
    # Ensure get_source_config returns the updated object
    pipeline._config.get_source_config = lambda provider: new_source_config

    # Create IdListRecordSourceImpl with new batch_size and replace it in extractor
    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=new_source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggerAdapterABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    # Mock parse_response to return empty list
    mock_extraction_service.parse_response.return_value = []
    mock_extraction_service.serialize_records.side_effect = lambda entity, recs: recs

    pipeline.extract()

    # Expect 3 calls: [1,2], [3,4], [5]
    assert mock_extraction_service.request_batch.call_count == 3

    calls = mock_extraction_service.request_batch.call_args_list
    # request_batch(entity, batch_ids, filter_key)
    assert calls[0][0][1] == ["1", "2"]
    assert calls[1][0][1] == ["3", "4"]
    assert calls[2][0][1] == ["5"]


def test_extract_missing_column(
    pipeline, mock_extraction_service, tmp_path, source_config
) -> None:
    """Test validation error when ID column is missing."""
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"wrong_col": [1]}).to_csv(csv_path, index=False)

    pipeline._config.input_mode = "id_only"
    pipeline._config.input_path = str(csv_path)

    # Create IdListRecordSourceImpl and replace it in extractor
    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggerAdapterABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    with pytest.raises(ValueError):
        pipeline.extract()
