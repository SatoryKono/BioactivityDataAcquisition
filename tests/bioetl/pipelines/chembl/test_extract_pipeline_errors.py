import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.errors import ClientNetworkError, PipelineStageError
from bioetl.infrastructure.config.models import PipelineConfig, ChemblSourceConfig
from bioetl.infrastructure.clients.chembl.provider import register_chembl_provider


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

    def bind(self, **ctx):  # pragma: no cover - delegating
        return self


def test_extract_stage_wraps_client_error(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    caplog.set_level("ERROR")

    register_chembl_provider()

    config = PipelineConfig(
        id="chembl.activity",
        provider="chembl",
        entity="activity",
        input_mode="auto_detect",
        input_path=None,
        output_path=str(tmp_path / "out"),
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
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

    pipeline = ChemblEntityPipeline(
        config=config,
        logger=logger,
        validation_service=validation_service,
        output_writer=output_writer,
        extraction_service=extraction_service,
        hash_service=hash_service,
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
