"""Tests for BatchProgressService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_progress_service import BatchProgressService


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_data_source() -> MagicMock:
    source = MagicMock()
    source.get_total_records = AsyncMock(return_value=100)
    return source


@pytest.fixture
def service(mock_logger: MagicMock, mock_data_source: MagicMock) -> BatchProgressService:
    return BatchProgressService(logger=mock_logger, data_source=mock_data_source)


@pytest.mark.asyncio
async def test_initialize_with_explicit_limit(
    service: BatchProgressService, mock_logger: MagicMock
) -> None:
    """When limit is provided, use it directly without querying data source."""
    await service.initialize_tracking(limit=50)

    assert service._total_records == 50
    assert service._progress_interval == 5  # max(1, 50 // 10)


@pytest.mark.asyncio
async def test_initialize_from_data_source(
    service: BatchProgressService, mock_data_source: MagicMock
) -> None:
    """When limit is None, query data source for total records."""
    await service.initialize_tracking(limit=None)

    mock_data_source.get_total_records.assert_awaited_once()
    assert service._total_records == 100
    assert service._progress_interval == 10


@pytest.mark.asyncio
async def test_initialize_no_total_available(mock_logger: MagicMock) -> None:
    """When data source has no get_total_records, progress tracking is disabled."""
    source = MagicMock(spec=[])  # No get_total_records
    svc = BatchProgressService(logger=mock_logger, data_source=source)

    await svc.initialize_tracking(limit=None)

    assert svc._total_records is None
    assert svc._progress_interval is None


def test_report_progress_emits_log(
    service: BatchProgressService, mock_logger: MagicMock
) -> None:
    """Emit progress log when threshold is reached."""
    service._total_records = 100
    service._progress_interval = 10
    service._next_progress_threshold = 10

    service.report_progress(
        records_fetched=15,
        records_bronze=14,
        records_silver=12,
        records_filtered_out=2,
    )

    mock_logger.info.assert_called()
    call_args = mock_logger.info.call_args
    assert "progress" in str(call_args) or "15%" in str(call_args)


def test_report_progress_below_threshold(
    service: BatchProgressService, mock_logger: MagicMock
) -> None:
    """No log emitted when below next threshold."""
    service._total_records = 100
    service._progress_interval = 10
    service._next_progress_threshold = 20

    service.report_progress(
        records_fetched=5,
        records_bronze=5,
        records_silver=4,
        records_filtered_out=1,
    )

    mock_logger.info.assert_not_called()


def test_report_progress_no_tracking(
    service: BatchProgressService, mock_logger: MagicMock
) -> None:
    """No log when progress tracking not initialized."""
    service._total_records = None
    service._progress_interval = None

    service.report_progress(
        records_fetched=50,
        records_bronze=50,
        records_silver=45,
        records_filtered_out=5,
    )

    mock_logger.info.assert_not_called()


def test_progress_threshold_advances(
    service: BatchProgressService, mock_logger: MagicMock
) -> None:
    """After reporting, next threshold advances by interval."""
    service._total_records = 100
    service._progress_interval = 10
    service._next_progress_threshold = 10

    service.report_progress(
        records_fetched=10,
        records_bronze=10,
        records_silver=9,
        records_filtered_out=1,
    )

    assert service._next_progress_threshold == 20
