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

    @pytest.fixture
    def mock_storage_with_vacuum(self):
        """Create a mock storage port with vacuum support."""
        storage = MagicMock()
        storage.clear_silver = AsyncMock(return_value=0)
        storage.clear_gold = AsyncMock(return_value=0)
        storage.vacuum = AsyncMock(return_value=42)
        storage.archive = AsyncMock(return_value=100)
        return storage

    @pytest.fixture
    def lifecycle_service_with_vacuum(self, mock_storage_with_vacuum, mock_logger):
        """Create a MedallionLifecycleService instance with vacuum support."""
        return MedallionLifecycleService(
            storage=mock_storage_with_vacuum,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_vacuum_delegates_to_storage(
        self, lifecycle_service_with_vacuum, mock_storage_with_vacuum
    ):
        """vacuum() should call storage.vacuum() with correct params."""
        result = await lifecycle_service_with_vacuum.vacuum(
            "chembl.activity", retention_days=7
        )

        assert result == 42
        mock_storage_with_vacuum.vacuum.assert_called_once_with(
            table_name="chembl.activity",
            retention_hours=168,
            dry_run=False,
        )

    @pytest.mark.asyncio
    async def test_vacuum_dry_run(
        self, lifecycle_service_with_vacuum, mock_storage_with_vacuum
    ):
        """vacuum() dry_run should pass flag to storage."""
        mock_storage_with_vacuum.vacuum.return_value = 10

        result = await lifecycle_service_with_vacuum.vacuum(
            "chembl.activity", retention_days=7, dry_run=True
        )

        assert result == 10
        mock_storage_with_vacuum.vacuum.assert_called_once_with(
            table_name="chembl.activity",
            retention_hours=168,
            dry_run=True,
        )

    @pytest.mark.asyncio
    async def test_vacuum_custom_retention(
        self, lifecycle_service_with_vacuum, mock_storage_with_vacuum
    ):
        """vacuum() should convert retention_days to hours."""
        await lifecycle_service_with_vacuum.vacuum(
            "chembl.activity", retention_days=30
        )

        mock_storage_with_vacuum.vacuum.assert_called_once_with(
            table_name="chembl.activity",
            retention_hours=720,  # 30 * 24
            dry_run=False,
        )

    @pytest.mark.asyncio
    async def test_vacuum_logs_operation(
        self, lifecycle_service_with_vacuum, mock_logger
    ):
        """vacuum() should log start and completion."""
        await lifecycle_service_with_vacuum.vacuum("chembl.activity")

        # Should have at least 2 log calls (start and complete)
        assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    async def test_vacuum_propagates_exception(
        self, lifecycle_service_with_vacuum, mock_storage_with_vacuum, mock_logger
    ):
        """vacuum() should propagate exceptions from storage."""
        mock_storage_with_vacuum.vacuum.side_effect = RuntimeError("Storage error")

        with pytest.raises(RuntimeError, match="Storage error"):
            await lifecycle_service_with_vacuum.vacuum("chembl.activity")

        # Should log error
        mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestMedallionLifecycleServiceArchive:
    """Test MedallionLifecycleService.archive method."""

    @pytest.fixture
    def mock_storage_with_archive(self):
        """Create a mock storage port with archive support."""
        storage = MagicMock()
        storage.clear_silver = AsyncMock(return_value=0)
        storage.clear_gold = AsyncMock(return_value=0)
        storage.vacuum = AsyncMock(return_value=0)
        storage.archive = AsyncMock(return_value=100)
        return storage

    @pytest.fixture
    def lifecycle_service_with_archive(self, mock_storage_with_archive, mock_logger):
        """Create a MedallionLifecycleService instance with archive support."""
        return MedallionLifecycleService(
            storage=mock_storage_with_archive,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_archive_delegates_to_storage(
        self, lifecycle_service_with_archive, mock_storage_with_archive
    ):
        """archive() should call storage.archive()."""
        result = await lifecycle_service_with_archive.archive(
            "chembl.activity", "/archive/2025"
        )

        assert result == 100
        mock_storage_with_archive.archive.assert_called_once_with(
            table_name="chembl.activity",
            target_path="/archive/2025",
            remove_source=False,
        )

    @pytest.mark.asyncio
    async def test_archive_with_remove_source(
        self, lifecycle_service_with_archive, mock_storage_with_archive
    ):
        """archive() should pass remove_source flag."""
        await lifecycle_service_with_archive.archive(
            "chembl.activity", "/archive/2025", remove_source=True
        )

        mock_storage_with_archive.archive.assert_called_once_with(
            table_name="chembl.activity",
            target_path="/archive/2025",
            remove_source=True,
        )

    @pytest.mark.asyncio
    async def test_archive_logs_operation(
        self, lifecycle_service_with_archive, mock_logger
    ):
        """archive() should log start and completion."""
        await lifecycle_service_with_archive.archive(
            "chembl.activity", "/archive/2025"
        )

        # Should have at least 2 log calls (start and complete)
        assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    async def test_archive_propagates_exception(
        self, lifecycle_service_with_archive, mock_storage_with_archive, mock_logger
    ):
        """archive() should propagate exceptions from storage."""
        mock_storage_with_archive.archive.side_effect = RuntimeError("Archive failed")

        with pytest.raises(RuntimeError, match="Archive failed"):
            await lifecycle_service_with_archive.archive(
                "chembl.activity", "/archive/2025"
            )

        # Should log error
        mock_logger.error.assert_called_once()
