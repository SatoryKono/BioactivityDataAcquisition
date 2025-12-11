"""
Tests for ChemblPipelineBase generic extract (via ChemblActivityPipeline).
"""

from typing import cast
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.configs import CsvInputConfig
from bioetl.domain.configs.pipeline import ChemblSourceConfig, ProviderHttpConfig
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry


def _extract_dataframe(pipeline: ChemblPipelineBase) -> pd.DataFrame:
    """Вспомогательный сбор всех чанков в единый DataFrame."""
    extract_result = pipeline.extract()
    if isinstance(extract_result, pd.DataFrame):
        chunks = [extract_result]
    else:
        chunks = list(extract_result)
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True)


@pytest.fixture
def source_config():
    """Create test ChemblSourceConfig with flat structure."""
    return ChemblSourceConfig(
        http=ProviderHttpConfig(
            base_url="https://test.com",
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=5.0,
        ),
        batch_size=100,
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
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.hashing = MagicMock()
    config.hashing.business_key_fields = ["activity_id"]
    config.primary_key = "activity_id"
    config.input_mode = "auto_detect"
    config.input_path = None
    config.csv_options = CsvInputConfig()
    config.model_dump.return_value = {}
    config.fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization
    return config


@pytest.fixture
def mock_extraction_service():
    service = MagicMock()
    service.extract_all.return_value = pd.DataFrame(
        {"activity_id": [1, 2, 3], "standard_flag": [1, 1, 1]}
    )
    service.iter_extract.return_value = iter(
        [
            [
                {"activity_id": 1, "standard_flag": True, "standard_value": 1.0},
                {"activity_id": 2, "standard_flag": True, "standard_value": 1.0},
                {"activity_id": 3, "standard_flag": True, "standard_value": 1.0},
            ]
        ]
    )
    service.request_batch.return_value = {
        "activities": [{"activity_id": 1, "standard_flag": True, "standard_value": 1.0}]
    }
    return service


@pytest.fixture
def mock_normalization_service():
    """Create mock normalization service."""
    service = MagicMock()
    service.apply_normalize_batch.side_effect = lambda df: df
    service.apply_normalize_dataframe.side_effect = lambda df: df
    service.normalize.side_effect = lambda df: df
    return service


@pytest.fixture
def pipeline(mock_config, mock_extraction_service, mock_normalization_service):
    """Create pipeline with mocked dependencies."""
    logger = MagicMock()
    validation_service = MagicMock()
    loader = MagicMock()
    metadata_builder = MagicMock()
    index_generator = MagicMock()
    index_generator.next_index.return_value = 0
    timestamp_provider = MagicMock()
    timestamp_provider.get_extraction_timestamp.return_value = "2024-01-01T00:00:00Z"
    hash_service = MagicMock()

    return ChemblPipelineBase(
        config=mock_config,
        logger=logger,
        validation_service=validation_service,
        loader=loader,
        extraction_service=mock_extraction_service,
        hash_service=hash_service,
        normalization_service=mock_normalization_service,
        metadata_builder=metadata_builder,
        index_generator=index_generator,
        timestamp_provider=timestamp_provider,
        entity_model_registry=get_chembl_model_registry(),
    )


def test_extract_no_input_file(pipeline, mock_extraction_service):
    """Test extraction uses record source to yield data."""
    pipeline._config.input_mode = "auto_detect"
    pipeline._config.input_path = None

    df = _extract_dataframe(pipeline)

    # Record source iter_records is used (not direct iter_extract call)
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
            "standard_flag": [True, True],
        }
    ).to_csv(csv_path, index=False)

    pipeline._config.input_mode = "csv"
    pipeline._config.input_path = str(csv_path)

    csv_record_source = CsvRecordSourceImpl(
        input_path=csv_path,
        csv_options=pipeline._config.csv_options,
        limit=None,
        logger=cast(LoggingPortABC, MagicMock()),
    )
    pipeline._extractor.record_source = csv_record_source

    df = _extract_dataframe(pipeline)

    assert len(df) == 2
    assert "standard_value" in df.columns
    # With record_source injection, extraction service methods are not called
    mock_extraction_service.extract_all.assert_not_called()
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

    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggingPortABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    mock_extraction_service.parse_response.return_value = [
        ActivityRawModel(activity_id="100", standard_flag=True, standard_value=1.0),
        ActivityRawModel(activity_id="101", standard_flag=True, standard_value=1.0),
        ActivityRawModel(activity_id="102", standard_flag=True, standard_value=1.0),
    ]

    mock_extraction_service.serialize_records.side_effect = lambda entity, recs: recs

    df = _extract_dataframe(pipeline)

    assert len(df) == 3
    mock_extraction_service.request_batch.assert_called()
    call_args = mock_extraction_service.request_batch.call_args
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
    new_source_config = ChemblSourceConfig(
        http=ProviderHttpConfig(
            base_url=source_config.http.base_url,
            timeout_sec=source_config.http.timeout_sec,
            max_retries=source_config.http.max_retries,
            rate_limit_per_sec=source_config.http.rate_limit_per_sec,
        ),
        batch_size=2,
    )
    pipeline._config.provider_config = new_source_config
    pipeline._config.get_source_config = lambda provider: new_source_config

    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=new_source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggingPortABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    mock_extraction_service.parse_response.return_value = []
    mock_extraction_service.serialize_records.side_effect = lambda entity, recs: recs

    list(pipeline.extract())

    assert mock_extraction_service.request_batch.call_count == 3

    calls = mock_extraction_service.request_batch.call_args_list
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

    id_list_record_source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=pipeline._config.csv_options,
        limit=None,
        extraction_service=mock_extraction_service,
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggingPortABC, MagicMock()),
        chunk_size=None,
    )
    pipeline._extractor.record_source = id_list_record_source

    with pytest.raises(ValueError):
        list(pipeline.extract())
