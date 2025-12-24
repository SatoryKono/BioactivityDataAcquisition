"""Unit tests for MedallionLifecycleService.

Tests the medallion layer lifecycle service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.medallion_lifecycle import (
    ClearResult,
    MedallionLifecycleService,
)
from bioetl.domain.medallion import ClearPolicy, MedallionPolicy


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_storage():
    """Create a mock storage port."""
    storage = MagicMock()
    storage.clear_silver = AsyncMock(return_value=0)
    storage.clear_gold = AsyncMock(return_value=0)
    return storage


@pytest.fixture
def lifecycle_service(mock_storage, mock_logger):
    """Create a MedallionLifecycleService instance."""
    return MedallionLifecycleService(
        storage=mock_storage,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestClearResult:
    """Test ClearResult dataclass."""

    def test_total_cleared(self):
        """Test total_cleared property."""
        result = ClearResult(silver_cleared=5, gold_cleared=3, dry_run=False)

        assert result.total_cleared == 8

    def test_total_cleared_with_zeros(self):
        """Test total_cleared with zero values."""
        result = ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False)

        assert result.total_cleared == 0

    def test_dry_run_flag(self):
        """Test dry_run flag is preserved."""
        result = ClearResult(silver_cleared=10, gold_cleared=5, dry_run=True)

        assert result.dry_run is True


@pytest.mark.unit
class TestMedallionLifecycleServiceClear:
    """Test MedallionLifecycleService.clear method."""

    @pytest.mark.asyncio
    async def test_clear_with_never_policy(self, lifecycle_service, mock_storage):
        """Test clear with NEVER policy doesn't call storage methods."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.NEVER)

        result = await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
        )

        # Should not call storage methods
        mock_storage.clear_silver.assert_not_called()
        mock_storage.clear_gold.assert_not_called()

        # Should return zero counts
        assert result.silver_cleared == 0
        assert result.gold_cleared == 0

    @pytest.mark.asyncio
    async def test_clear_with_silver_only_policy(self, lifecycle_service, mock_storage):
        """Test clear with SILVER_ONLY policy clears only Silver."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_ONLY)
        mock_storage.clear_silver.return_value = 10

        result = await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
        )

        # Should only clear Silver
        mock_storage.clear_silver.assert_called_once_with(
            "test_silver", dry_run=False
        )
        mock_storage.clear_gold.assert_not_called()

        assert result.silver_cleared == 10
        assert result.gold_cleared == 0

    @pytest.mark.asyncio
    async def test_clear_with_silver_and_gold_policy(
        self, lifecycle_service, mock_storage
    ):
        """Test clear with SILVER_AND_GOLD policy clears both layers."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        result = await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
        )

        # Should clear both layers
        mock_storage.clear_silver.assert_called_once_with(
            "test_silver", dry_run=False
        )
        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=False)

        assert result.silver_cleared == 10
        assert result.gold_cleared == 5

    @pytest.mark.asyncio
    async def test_clear_passes_dry_run_flag(self, lifecycle_service, mock_storage):
        """Test clear passes dry_run flag to storage methods."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        result = await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        # Should pass dry_run=True
        mock_storage.clear_silver.assert_called_once_with("test_silver", dry_run=True)
        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=True)

        assert result.dry_run is True

    @pytest.mark.asyncio
    async def test_clear_logs_dry_run(self, lifecycle_service, mock_storage, mock_logger):
        """Test clear logs correctly in dry run mode."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=True,
        )

        # Should log dry run message
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "DRY RUN" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_clear_logs_when_records_cleared(
        self, lifecycle_service, mock_storage, mock_logger
    ):
        """Test clear logs when records are actually cleared."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        # Should log cleared message
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Cleared storage" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_clear_no_log_when_nothing_cleared(
        self, lifecycle_service, mock_storage, mock_logger
    ):
        """Test clear does not log when nothing was cleared."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)
        mock_storage.clear_silver.return_value = 0
        mock_storage.clear_gold.return_value = 0

        await lifecycle_service.clear(
            policy=policy,
            silver_table="test_silver",
            gold_table="test_gold",
            dry_run=False,
        )

        # Should not log when nothing cleared
        mock_logger.info.assert_not_called()


@pytest.mark.unit
class TestMedallionLifecycleServiceVacuum:
    """Test MedallionLifecycleService.vacuum method."""

    @pytest.mark.asyncio
    async def test_vacuum_not_implemented(self, lifecycle_service):
        """Test vacuum raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Vacuum not yet implemented"):
            await lifecycle_service.vacuum("test_table")


@pytest.mark.unit
class TestMedallionLifecycleServiceArchive:
    """Test MedallionLifecycleService.archive method."""

    @pytest.mark.asyncio
    async def test_archive_not_implemented(self, lifecycle_service):
        """Test archive raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Archive not yet implemented"):
            await lifecycle_service.archive("test_table", "/archive/path")
