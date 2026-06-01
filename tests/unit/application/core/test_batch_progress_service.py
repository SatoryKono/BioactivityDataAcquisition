"""Tests for BatchProgressService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_progress_service import BatchProgressService


pytestmark = pytest.mark.unit

@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_data_source() -> MagicMock:
    source = MagicMock()
    source.get_total_records = AsyncMock(return_value=100)
    return source


@pytest.fixture
def service(
    mock_logger: MagicMock, mock_data_source: MagicMock
) -> BatchProgressService:
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


# ---------------------------------------------------------------------------
# Additional branch-coverage tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInitializeTrackingEdgeCases:
    """Additional edge-case tests for BatchProgressService.initialize_tracking."""

    async def test_does_not_query_data_source_when_limit_given(
        self, mock_logger: MagicMock, mock_data_source: MagicMock
    ) -> None:
        """Data source get_total_records is NOT awaited when limit is provided."""
        svc = BatchProgressService(logger=mock_logger, data_source=mock_data_source)
        await svc.initialize_tracking(limit=500)
        mock_data_source.get_total_records.assert_not_awaited()

    async def test_ignores_zero_from_data_source(self, mock_logger: MagicMock) -> None:
        """Zero total from data source does not set _total_records."""
        ds = MagicMock()
        ds.get_total_records = AsyncMock(return_value=0)
        svc = BatchProgressService(logger=mock_logger, data_source=ds)
        await svc.initialize_tracking(limit=None)
        assert svc._total_records is None

    async def test_ignores_non_int_from_data_source(
        self, mock_logger: MagicMock
    ) -> None:
        """Non-int result from data source is ignored."""
        ds = MagicMock()
        ds.get_total_records = AsyncMock(return_value="many")
        svc = BatchProgressService(logger=mock_logger, data_source=ds)
        await svc.initialize_tracking(limit=None)
        assert svc._total_records is None

    async def test_data_source_without_get_total_records_attr(
        self, mock_logger: MagicMock
    ) -> None:
        """Data source without get_total_records handled without AttributeError."""
        ds = MagicMock(spec=[])
        svc = BatchProgressService(logger=mock_logger, data_source=ds)
        await svc.initialize_tracking(limit=None)
        assert svc._total_records is None
        assert svc._progress_interval is None


@pytest.mark.unit
class TestSetProgressThresholds:
    """Unit tests for BatchProgressService._set_progress_thresholds."""

    def test_interval_is_tenth_of_total(self, mock_logger: MagicMock) -> None:
        """_progress_interval is max(1, total // 10)."""
        svc = BatchProgressService(logger=mock_logger, data_source=MagicMock(spec=[]))
        svc._total_records = 200
        svc._set_progress_thresholds()
        assert svc._progress_interval == 20

    def test_minimum_interval_is_1(self, mock_logger: MagicMock) -> None:
        """Interval is at least 1 for tiny totals."""
        svc = BatchProgressService(logger=mock_logger, data_source=MagicMock(spec=[]))
        svc._total_records = 3
        svc._set_progress_thresholds()
        assert svc._progress_interval >= 1

    def test_next_threshold_equals_interval_after_init(
        self, mock_logger: MagicMock
    ) -> None:
        """First threshold equals the computed interval."""
        svc = BatchProgressService(logger=mock_logger, data_source=MagicMock(spec=[]))
        svc._total_records = 100
        svc._set_progress_thresholds()
        assert svc._next_progress_threshold == svc._progress_interval

    def test_no_op_when_total_is_none(self, mock_logger: MagicMock) -> None:
        """_set_progress_thresholds is a no-op when _total_records is None."""
        svc = BatchProgressService(logger=mock_logger, data_source=MagicMock(spec=[]))
        svc._total_records = None
        svc._set_progress_thresholds()
        assert svc._progress_interval is None

    def test_logs_starting_info_with_total_and_interval(
        self, mock_logger: MagicMock
    ) -> None:
        """Info log includes total_records and progress_interval."""
        svc = BatchProgressService(logger=mock_logger, data_source=MagicMock(spec=[]))
        svc._total_records = 500
        svc._set_progress_thresholds()
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["total_records"] == 500
        assert "progress_interval" in call_kwargs


@pytest.mark.unit
class TestReportProgressDetail:
    """Detailed branch tests for BatchProgressService.report_progress."""

    def test_progress_log_includes_bronze_silver_filtered(
        self, service: BatchProgressService, mock_logger: MagicMock
    ) -> None:
        """Log message includes all four counter fields."""
        service._total_records = 100
        service._progress_interval = 10
        service._next_progress_threshold = 10

        service.report_progress(
            records_fetched=10,
            records_bronze=9,
            records_silver=7,
            records_filtered_out=3,
        )

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["bronze"] == 9
        assert call_kwargs["silver"] == 7
        assert call_kwargs["filtered_out"] == 3
        assert call_kwargs["fetched"] == 10

    def test_progress_percentage_format(
        self, service: BatchProgressService, mock_logger: MagicMock
    ) -> None:
        """Progress field is formatted as a percentage string ending in '%'."""
        service._total_records = 100
        service._progress_interval = 10
        service._next_progress_threshold = 10

        service.report_progress(
            records_fetched=10,
            records_bronze=10,
            records_silver=10,
            records_filtered_out=0,
        )

        call_kwargs = mock_logger.info.call_args[1]
        pct = call_kwargs["progress"]
        assert pct.endswith("%"), f"Expected '%' suffix, got: {pct!r}"

    def test_progress_capped_at_100_percent(
        self, service: BatchProgressService, mock_logger: MagicMock
    ) -> None:
        """Progress never exceeds 100% even when more records than total are fetched."""
        service._total_records = 10
        service._progress_interval = 1
        service._next_progress_threshold = 1

        service.report_progress(
            records_fetched=999,
            records_bronze=999,
            records_silver=999,
            records_filtered_out=0,
        )

        call_kwargs = mock_logger.info.call_args[1]
        pct_val = float(call_kwargs["progress"].rstrip("%"))
        assert pct_val <= 100.0

    def test_multiple_threshold_crossings_accumulate_logs(
        self, service: BatchProgressService, mock_logger: MagicMock
    ) -> None:
        """Each threshold crossing produces exactly one additional log call."""
        service._total_records = 100
        service._progress_interval = 10
        service._next_progress_threshold = 10

        for fetched in [10, 20, 30]:
            service.report_progress(
                records_fetched=fetched,
                records_bronze=fetched,
                records_silver=fetched,
                records_filtered_out=0,
            )

        assert mock_logger.info.call_count == 3
