import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.data_flow import DataFlowConfig
from bioetl.domain.configs.identity import PipelineIdentityConfig
from bioetl.domain.configs.pipeline import ChemblSourceConfig, ProviderHttpConfig
from bioetl.domain.configs.sink import DataSinkConfig
from bioetl.domain.configs.source import DataSourceConfig
from bioetl.domain.errors import ClientNetworkError, PipelineStageError
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry


class _LoggerStub:
    def __init__(self, logger) -> None:
        self._logger = logger

    def info(self, msg: str, **ctx):  # pragma: no cover - delegating
        self._logger.info(msg, extra=ctx)

    def error(self, msg: str, **ctx):  # pragma: no cover - delegating
        self._logger.error(msg, extra=ctx)

    def debug(self, msg: str, **ctx):  # pragma: no cover - delegating
        self._logger.debug(msg, extra=ctx)

    def warning(self, msg: str, **ctx):  # pragma: no cover - delegating
        self._logger.warning(msg, extra=ctx)

    def apply_bind(self, **ctx):  # pragma: no cover - delegating
        return self


def test_extract_stage_wraps_client_error(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    caplog.set_level("ERROR")

    config = PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="chembl.activity",
            provider="chembl",
            entity="activity",
            primary_key=["activity_id"],
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                input_path=None,
                batch_size=10,
            ),
            sink=DataSinkConfig(
                output_path=str(tmp_path / "out"),
            ),
        ),
        provider_config=ChemblSourceConfig(
            http=ProviderHttpConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    extraction_service = MagicMock(spec=ExtractionServiceABC)
    extraction_service.iter_extract.side_effect = ClientNetworkError(
        provider="chembl", endpoint="/status", message="timeout"
    )

    validation_service = MagicMock()
    validation_service.validate.side_effect = lambda df, entity_name=None: df

    output_writer = MagicMock()

    hash_service = MagicMock()

    logger = _LoggerStub(logging.getLogger("pipeline-test"))

    normalization_service = MagicMock()
    normalization_service.apply_normalize_dataframe.side_effect = lambda df: df
    normalization_service.apply_normalize_batch.side_effect = lambda df: df
    normalization_service.normalize.side_effect = lambda df: df
    normalization_service.apply_normalize_fields.side_effect = lambda df, *_: df
    normalization_service.apply_normalize.side_effect = lambda record: record

    index_generator = MagicMock()
    index_generator.next_index.return_value = 0
    timestamp_provider = MagicMock()
    timestamp_provider.get_extraction_timestamp.return_value = "2024-01-01T00:00:00Z"

    pipeline = ChemblPipelineBase(
        config=config,
        logger=logger,
        validation_service=validation_service,
        loader=output_writer,
        extraction_service=extraction_service,
        hash_service=hash_service,
        normalization_service=normalization_service,
        index_generator=index_generator,
        timestamp_provider=timestamp_provider,
        entity_model_registry=get_chembl_model_registry(),
    )

    with pytest.raises(PipelineStageError) as exc_info:
        pipeline.run(output_path=tmp_path / "out.parquet")

    error = exc_info.value

    assert isinstance(error.cause, ClientNetworkError)
    assert error.provider == "chembl"
    assert error.entity == "activity"
    assert error.stage == "extract"
    assert error.attempt == 1

    log_text = caplog.text
    assert "Stage failed" in log_text
    assert "Pipeline failed" in log_text
