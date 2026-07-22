"""Additional coverage tests for DQReportService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC
from tests.helpers.deterministic_ids import deterministic_uuid_string_from_callsite

import pytest

from bioetl.application.services.dq_report_service import (
    DQReportService,
    DQReportContext,
)
from bioetl.domain.ports import (
    BronzeDQAnalyzerPort,
    SilverDQAnalyzerPort,
    GoldDQAnalyzerPort,
    DQReportWriterPort,
    BronzeDQConfigPort,
)


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_bronze_analyzer():
    return MagicMock(spec=BronzeDQAnalyzerPort)


@pytest.fixture
def mock_silver_analyzer():
    return MagicMock(spec=SilverDQAnalyzerPort)


@pytest.fixture
def mock_gold_analyzer():
    return MagicMock(spec=GoldDQAnalyzerPort)


@pytest.fixture
def mock_writer():
    return AsyncMock(spec=DQReportWriterPort)


@pytest.fixture
def service(
    mock_logger,
    mock_bronze_analyzer,
    mock_silver_analyzer,
    mock_gold_analyzer,
    mock_writer,
):
    return DQReportService(
        logger=mock_logger,
        bronze_analyzer=mock_bronze_analyzer,
        silver_analyzer=mock_silver_analyzer,
        gold_analyzer=mock_gold_analyzer,
        report_writer=mock_writer,
    )


@pytest.fixture
def context():
    return DQReportContext(
        run_id=deterministic_uuid_string_from_callsite(
            "test_dq_report_service_coverage"
        ),
        pipeline_name="test_pipeline",
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="test",
        entity="test",
        bronze_records=[b"record"],
        bronze_batch_id="batch1",
        bronze_source_file="file.json",
    )


@pytest.mark.asyncio
async def test_generate_bronze_report_error(service, context, mock_bronze_analyzer):
    """Test error handling in _generate_bronze_report."""
    from bioetl.domain.exceptions import DataQualityError

    config = MagicMock(spec=BronzeDQConfigPort)
    config.enabled = True

    for error in (
        DataQualityError("Analysis failed"),
        TimeoutError("Analysis timed out"),
    ):
        mock_bronze_analyzer.analyze.side_effect = error

        result = await service._generate_bronze_report(context, config)

        assert result is None
        service._logger.error.assert_called_once_with(
            "bronze_dq_report_failed", run_id=context.run_id, error=str(error)
        )
        service._logger.reset_mock()


@pytest.mark.asyncio
async def test_generate_bronze_report_writer_error(
    service, context, mock_bronze_analyzer, mock_writer
):
    """Test error handling when writer fails."""
    mock_bronze_analyzer.analyze.return_value = MagicMock()
    mock_writer.write_bronze_report.side_effect = OSError("Write failed")

    config = MagicMock(spec=BronzeDQConfigPort)
    config.enabled = True

    result = await service._generate_bronze_report(context, config)

    assert result is None
    service._logger.error.assert_called()
