"""Unit tests for CleanupService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.cleanup_service import CleanupService
from bioetl.domain.types import CleanupPreview, CleanupResult, LayerPreview


@pytest.fixture
def mock_storage():
    """Create a mock storage port."""
    storage = MagicMock()
    storage.preview_cleanup = MagicMock(
        return_value={
            "silver": {"path": "/data/silver/test_table", "file_count": 10, "exists": True},
            "gold": {"path": "/data/gold/test_table", "file_count": 5, "exists": True},
            "total_files": 15,
        }
    )
    storage.clear_silver = AsyncMock(return_value=10)
    storage.clear_gold = AsyncMock(return_value=5)
    return storage


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def cleanup_service(mock_storage, mock_logger):
    """Create a CleanupService instance."""
    return CleanupService(storage=mock_storage, logger=mock_logger)


@pytest.mark.unit
class TestCleanupServiceInit:
    """Tests for CleanupService initialization."""

    def test_initialization(self, mock_storage, mock_logger):
        """Test service initializes correctly."""
        service = CleanupService(storage=mock_storage, logger=mock_logger)

        assert service._storage == mock_storage
        assert service._logger == mock_logger


@pytest.mark.unit
class TestCleanupServicePreview:
    """Tests for CleanupService.preview method."""

    @pytest.mark.asyncio
    async def test_preview_returns_cleanup_preview(self, cleanup_service, mock_storage):
        """Test preview returns typed CleanupPreview."""
        result = await cleanup_service.preview(
            silver_table="test_silver",
            gold_table="test_gold",
        )

        assert isinstance(result, CleanupPreview)
        assert isinstance(result.silver, LayerPreview)
        assert result.silver.path == "/data/silver/test_table"
        assert result.silver.file_count == 10
        assert result.silver.exists is True

    @pytest.mark.asyncio
    async def test_preview_with_gold_table(self, cleanup_service, mock_storage):
        """Test preview includes gold layer info when gold_table is provided."""
        result = await cleanup_service.preview(
            silver_table="test_silver",
            gold_table="test_gold",
        )

        assert result.gold is not None
        assert isinstance(result.gold, LayerPreview)
        assert result.gold.path == "/data/gold/test_table"
        assert result.gold.file_count == 5
        assert result.gold.exists is True

    @pytest.mark.asyncio
    async def test_preview_without_gold_table(self, mock_storage, mock_logger):
        """Test preview returns None for gold when gold_table not provided."""
        mock_storage.preview_cleanup.return_value = {
            "silver": {"path": "/data/silver/test_table", "file_count": 10, "exists": True},
            "gold": None,
            "total_files": 10,
        }
        service = CleanupService(storage=mock_storage, logger=mock_logger)

        result = await service.preview(silver_table="test_silver", gold_table=None)

        assert result.gold is None
        assert result.total_files == 10

    @pytest.mark.asyncio
    async def test_preview_calls_storage_preview_cleanup(
        self, cleanup_service, mock_storage
    ):
        """Test preview calls storage.preview_cleanup with correct arguments."""
        await cleanup_service.preview(
            silver_table="my_silver",
            gold_table="my_gold",
        )

        mock_storage.preview_cleanup.assert_called_once_with(
            silver_table="my_silver",
            gold_table="my_gold",
        )

    @pytest.mark.asyncio
    async def test_preview_total_files_count(self, cleanup_service):
        """Test preview returns correct total_files count."""
        result = await cleanup_service.preview(
            silver_table="test_silver",
            gold_table="test_gold",
        )

        assert result.total_files == 15


@pytest.mark.unit
class TestCleanupServiceExecuteDryRun:
    """Tests for CleanupService.execute method with dry_run=True."""

    @pytest.mark.asyncio
    async def test_execute_dry_run_returns_cleanup_result(
        self, cleanup_service, mock_storage
    ):
        """Test execute with dry_run returns typed CleanupResult."""
        result = await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        assert isinstance(result, CleanupResult)
        assert result.dry_run is True

    @pytest.mark.asyncio
    async def test_execute_dry_run_calls_storage_with_dry_run_flag(
        self, cleanup_service, mock_storage
    ):
        """Test execute passes dry_run=True to storage methods."""
        await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        mock_storage.clear_silver.assert_called_once_with("test_silver", dry_run=True)
        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=True)

    @pytest.mark.asyncio
    async def test_execute_dry_run_logs_preview_message(
        self, cleanup_service, mock_logger
    ):
        """Test execute with dry_run logs appropriate message."""
        await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert "DRY RUN" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_dry_run_returns_counts(self, cleanup_service):
        """Test execute with dry_run returns correct counts."""
        result = await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        assert result.silver_cleared == 10
        assert result.gold_cleared == 5
        assert result.total_cleared == 15


@pytest.mark.unit
class TestCleanupServiceExecuteActual:
    """Tests for CleanupService.execute method with dry_run=False."""

    @pytest.mark.asyncio
    async def test_execute_actual_returns_cleanup_result(
        self, cleanup_service, mock_storage
    ):
        """Test execute without dry_run returns typed CleanupResult."""
        result = await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        assert isinstance(result, CleanupResult)
        assert result.dry_run is False

    @pytest.mark.asyncio
    async def test_execute_actual_calls_storage_without_dry_run(
        self, cleanup_service, mock_storage
    ):
        """Test execute passes dry_run=False to storage methods."""
        await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        mock_storage.clear_silver.assert_called_once_with("test_silver", dry_run=False)
        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=False)

    @pytest.mark.asyncio
    async def test_execute_actual_logs_cleared_message(
        self, cleanup_service, mock_logger
    ):
        """Test execute without dry_run logs cleared message when files cleared."""
        await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert "Cleared storage" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_actual_no_log_when_nothing_cleared(
        self, mock_storage, mock_logger
    ):
        """Test execute does not log when nothing is cleared."""
        mock_storage.clear_silver = AsyncMock(return_value=0)
        mock_storage.clear_gold = AsyncMock(return_value=0)
        service = CleanupService(storage=mock_storage, logger=mock_logger)

        await service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        # info should not be called when nothing is cleared
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert not any("Cleared storage" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_execute_actual_returns_correct_counts(self, cleanup_service):
        """Test execute returns correct counts after actual cleanup."""
        result = await cleanup_service.execute(
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        assert result.silver_cleared == 10
        assert result.gold_cleared == 5
        assert result.total_cleared == 15


@pytest.mark.unit
class TestCleanupServiceExecuteWithoutGold:
    """Tests for CleanupService.execute without gold table."""

    @pytest.mark.asyncio
    async def test_execute_without_gold_table(self, mock_storage, mock_logger):
        """Test execute only clears silver when gold_table is None."""
        service = CleanupService(storage=mock_storage, logger=mock_logger)

        result = await service.execute(
            silver_table="test_silver",
            gold_table=None,
            dry_run=False,
        )

        mock_storage.clear_silver.assert_called_once()
        mock_storage.clear_gold.assert_not_called()
        assert result.gold_cleared == 0

    @pytest.mark.asyncio
    async def test_execute_without_gold_returns_silver_only_count(
        self, mock_storage, mock_logger
    ):
        """Test execute returns correct total when only silver is cleared."""
        service = CleanupService(storage=mock_storage, logger=mock_logger)

        result = await service.execute(
            silver_table="test_silver",
            gold_table=None,
            dry_run=False,
        )

        assert result.silver_cleared == 10
        assert result.gold_cleared == 0
        assert result.total_cleared == 10
