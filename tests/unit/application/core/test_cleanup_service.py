# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for CleanupService.

Tests the unified cleanup service for Silver and Gold layers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.core.lifecycle.cleanup_service import (
    CleanupPreview,
    CleanupResult,
    CleanupService,
    LayerInfo,
)


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
    storage.preview_cleanup = MagicMock(
        return_value={
            "silver": {"path": "/data/silver/test", "file_count": 10, "exists": True},
            "gold": {"path": "/data/gold/test", "file_count": 5, "exists": True},
            "total_files": 15,
        }
    )
    return storage


@pytest.fixture
def cleanup_service(mock_storage, mock_logger):
    """Create a CleanupService instance."""
    return CleanupService(storage=mock_storage, logger=mock_logger)


@pytest.mark.unit
class TestLayerInfo:
    """Test LayerInfo dataclass."""

    def test_layer_info_creation(self):
        """Test LayerInfo creation with all fields."""
        info = LayerInfo(path="/data/silver/test", file_count=10, exists=True)

        assert info.path == "/data/silver/test"
        assert info.file_count == 10
        assert info.exists is True

    def test_layer_info_immutable(self):
        """Test LayerInfo is immutable."""
        info = LayerInfo(path="/data/silver/test", file_count=10, exists=True)

        with pytest.raises(AttributeError):
            info.path = "/new/path"  # type: ignore[misc]


@pytest.mark.unit
class TestCleanupPreview:
    """Test CleanupPreview dataclass."""

    def test_cleanup_preview_creation(self):
        """Test CleanupPreview creation."""
        silver = LayerInfo(path="/data/silver", file_count=10, exists=True)
        gold = LayerInfo(path="/data/gold", file_count=5, exists=True)

        preview = CleanupPreview(silver=silver, gold=gold, total_files=15)

        assert preview.silver == silver
        assert preview.gold == gold
        assert preview.total_files == 15

    def test_cleanup_preview_with_no_gold(self):
        """Test CleanupPreview with no gold layer."""
        silver = LayerInfo(path="/data/silver", file_count=10, exists=True)

        preview = CleanupPreview(silver=silver, gold=None, total_files=10)

        assert preview.gold is None


@pytest.mark.unit
class TestCleanupResult:
    """Test CleanupResult dataclass."""

    def test_total_cleared(self):
        """Test total_cleared property."""
        result = CleanupResult(silver_cleared=5, gold_cleared=3, dry_run=False)

        assert result.total_cleared == 8

    def test_total_cleared_with_zeros(self):
        """Test total_cleared with zero values."""
        result = CleanupResult(silver_cleared=0, gold_cleared=0, dry_run=False)

        assert result.total_cleared == 0

    def test_dry_run_flag(self):
        """Test dry_run flag is preserved."""
        result = CleanupResult(silver_cleared=10, gold_cleared=5, dry_run=True)

        assert result.dry_run is True


@pytest.mark.unit
class TestCleanupServicePreview:
    """Test CleanupService.preview method."""

    @pytest.mark.asyncio
    async def test_preview_returns_cleanup_preview(self, cleanup_service):
        """Test preview returns CleanupPreview dataclass."""
        result = await cleanup_service.preview(
            silver_table="test_silver", gold_table="test_gold"
        )

        assert isinstance(result, CleanupPreview)

    @pytest.mark.asyncio
    async def test_preview_calls_storage_preview_cleanup(
        self, cleanup_service, mock_storage
    ):
        """Test preview calls storage.preview_cleanup."""
        await cleanup_service.preview(
            silver_table="test_silver", gold_table="test_gold"
        )

        mock_storage.preview_cleanup.assert_called_once_with(
            silver_table="test_silver", gold_table="test_gold"
        )

    @pytest.mark.asyncio
    async def test_preview_parses_silver_info(self, cleanup_service, mock_storage):
        """Test preview correctly parses silver layer info."""
        mock_storage.preview_cleanup.return_value = {
            "silver": {"path": "/path/to/silver", "file_count": 42, "exists": True},
            "gold": None,
            "total_files": 42,
        }

        result = await cleanup_service.preview(
            silver_table="test_silver", gold_table=None
        )

        assert result.silver.path == "/path/to/silver"
        assert result.silver.file_count == 42
        assert result.silver.exists is True

    @pytest.mark.asyncio
    async def test_preview_parses_gold_info(self, cleanup_service, mock_storage):
        """Test preview correctly parses gold layer info."""
        mock_storage.preview_cleanup.return_value = {
            "silver": {"path": "/path/to/silver", "file_count": 10, "exists": True},
            "gold": {"path": "/path/to/gold", "file_count": 5, "exists": False},
            "total_files": 15,
        }

        result = await cleanup_service.preview(
            silver_table="test_silver", gold_table="test_gold"
        )

        assert result.gold is not None
        assert result.gold.path == "/path/to/gold"
        assert result.gold.file_count == 5
        assert result.gold.exists is False

    @pytest.mark.asyncio
    async def test_preview_handles_no_gold(self, cleanup_service, mock_storage):
        """Test preview handles case when gold is None."""
        mock_storage.preview_cleanup.return_value = {
            "silver": {"path": "/path/to/silver", "file_count": 10, "exists": True},
            "gold": None,
            "total_files": 10,
        }

        result = await cleanup_service.preview(
            silver_table="test_silver", gold_table=None
        )

        assert result.gold is None

    @pytest.mark.asyncio
    async def test_preview_logs_debug(self, cleanup_service, mock_logger):
        """Test preview logs debug message."""
        await cleanup_service.preview(
            silver_table="test_silver", gold_table="test_gold"
        )

        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["silver_table"] == "test_silver"
        assert call_kwargs["gold_table"] == "test_gold"


@pytest.mark.unit
class TestCleanupServiceExecute:
    """Test CleanupService.execute method."""

    @pytest.mark.asyncio
    async def test_execute_returns_cleanup_result(self, cleanup_service):
        """Test execute returns CleanupResult dataclass."""
        result = await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold"
        )

        assert isinstance(result, CleanupResult)

    @pytest.mark.asyncio
    async def test_execute_clears_silver(self, cleanup_service, mock_storage):
        """Test execute clears silver table."""
        mock_storage.clear_silver.return_value = 10

        result = await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold"
        )

        mock_storage.clear_silver.assert_called_once_with("test_silver", dry_run=False)
        assert result.silver_cleared == 10

    @pytest.mark.asyncio
    async def test_execute_clears_gold(self, cleanup_service, mock_storage):
        """Test execute clears gold table."""
        mock_storage.clear_gold.return_value = 5

        result = await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold"
        )

        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=False)
        assert result.gold_cleared == 5

    @pytest.mark.asyncio
    async def test_execute_skips_gold_when_none(self, cleanup_service, mock_storage):
        """Test execute skips gold when gold_table is None."""
        await cleanup_service.execute(silver_table="test_silver", gold_table=None)

        mock_storage.clear_silver.assert_called_once()
        mock_storage.clear_gold.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_passes_dry_run_flag(self, cleanup_service, mock_storage):
        """Test execute passes dry_run flag to storage methods."""
        await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold", dry_run=True
        )

        mock_storage.clear_silver.assert_called_once_with("test_silver", dry_run=True)
        mock_storage.clear_gold.assert_called_once_with("test_gold", dry_run=True)

    @pytest.mark.asyncio
    async def test_execute_result_has_dry_run_flag(self, cleanup_service):
        """Test execute result includes dry_run flag."""
        result = await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold", dry_run=True
        )

        assert result.dry_run is True

    @pytest.mark.asyncio
    async def test_execute_logs_dry_run(
        self, cleanup_service, mock_storage, mock_logger
    ):
        """Test execute logs correctly in dry run mode."""
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold", dry_run=True
        )

        # Should log dry run message
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "DRY RUN" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_logs_when_records_cleared(
        self, cleanup_service, mock_storage, mock_logger
    ):
        """Test execute logs when records are actually cleared."""
        mock_storage.clear_silver.return_value = 10
        mock_storage.clear_gold.return_value = 5

        await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold", dry_run=False
        )

        # Should log cleared message
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Cleared storage" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_no_log_when_nothing_cleared(
        self, cleanup_service, mock_storage, mock_logger
    ):
        """Test execute does not log when nothing was cleared."""
        mock_storage.clear_silver.return_value = 0
        mock_storage.clear_gold.return_value = 0

        await cleanup_service.execute(
            silver_table="test_silver", gold_table="test_gold", dry_run=False
        )

        # Should not log when nothing cleared
        mock_logger.info.assert_not_called()


@pytest.mark.unit
class TestCleanupServiceIntegration:
    """Integration tests for CleanupService with runner scenarios."""

    @pytest.mark.asyncio
    async def test_execute_for_rebuild_scenario(self, cleanup_service, mock_storage):
        """Test execute for rebuild scenario (both tables cleared)."""
        mock_storage.clear_silver.return_value = 100
        mock_storage.clear_gold.return_value = 50

        result = await cleanup_service.execute(
            silver_table="chembl_activity",
            gold_table="chembl.activity",
            dry_run=False,
        )

        assert result.silver_cleared == 100
        assert result.gold_cleared == 50
        assert result.total_cleared == 150
        assert result.dry_run is False

    @pytest.mark.asyncio
    async def test_execute_dry_run_for_cli_preview(
        self, cleanup_service, mock_storage, mock_logger
    ):
        """Test execute with dry_run=True for CLI preview scenario."""
        mock_storage.clear_silver.return_value = 100
        mock_storage.clear_gold.return_value = 50

        result = await cleanup_service.execute(
            silver_table="chembl_activity",
            gold_table="chembl.activity",
            dry_run=True,
        )

        # Should return counts but with dry_run=True
        assert result.silver_cleared == 100
        assert result.gold_cleared == 50
        assert result.dry_run is True

        # Should log DRY RUN message
        mock_logger.info.assert_called_once()
        assert "DRY RUN" in str(mock_logger.info.call_args)


@pytest.mark.unit
class TestCleanupServicePreviewThreadOffload:
    """Regression: preview must not block the event loop on sync FS scans."""

    @pytest.mark.asyncio
    async def test_preview_offloads_sync_scan_to_thread(
        self, cleanup_service, mock_storage
    ) -> None:
        """preview_cleanup is invoked via asyncio.to_thread."""
        with patch(
            "bioetl.application.core.lifecycle.cleanup_service.asyncio.to_thread",
            new=AsyncMock(side_effect=lambda fn, **kwargs: fn(**kwargs)),
        ) as to_thread:
            await cleanup_service.preview(
                silver_table="test_silver", gold_table="test_gold"
            )
        to_thread.assert_awaited_once()
        call = to_thread.await_args
        assert call is not None
        assert call.args[0] is mock_storage.preview_cleanup
        assert call.kwargs == {
            "silver_table": "test_silver",
            "gold_table": "test_gold",
        }
