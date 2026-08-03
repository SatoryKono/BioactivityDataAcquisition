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
"""Unit tests for BronzeCleanupService.

Tests the bronze cleanup administrative service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.bronze_cleanup_service import (
    BronzeCleanupResult,
    BronzeCleanupService,
)
from tests.helpers.clock import FixedClock


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
    storage.cleanup_bronze = AsyncMock(
        return_value={
            "files_removed": 0,
            "bytes_freed": 0,
            "directories_removed": 0,
        }
    )
    return storage


@pytest.fixture
def bronze_cleanup_service(mock_storage, mock_logger):
    """Create a BronzeCleanupService instance."""
    now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    return BronzeCleanupService(
        storage=mock_storage,
        logger=mock_logger,
        clock=FixedClock(now),
    )


@pytest.mark.unit
class TestBronzeCleanupResult:
    """Test BronzeCleanupResult dataclass."""

    def test_cleanup_result_creation(self):
        """Test BronzeCleanupResult can be created."""
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        result = BronzeCleanupResult(
            files_removed=10,
            bytes_freed=1024 * 1024,
            directories_removed=5,
            dry_run=False,
            cutoff_date=now,
        )

        assert result.files_removed == 10
        assert result.bytes_freed == 1024 * 1024
        assert result.directories_removed == 5
        assert result.dry_run is False
        assert result.cutoff_date == now

    def test_cleanup_result_dry_run(self):
        """Test BronzeCleanupResult with dry_run flag."""
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        result = BronzeCleanupResult(
            files_removed=10,
            bytes_freed=1024 * 1024,
            directories_removed=5,
            dry_run=True,
            cutoff_date=now,
        )

        assert result.dry_run is True


@pytest.mark.unit
class TestBronzeCleanupServiceCleanup:
    """Test BronzeCleanupService.cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_with_defaults(self, bronze_cleanup_service, mock_storage):
        """Test cleanup with default retention (90 days)."""
        mock_storage.cleanup_bronze.return_value = {
            "files_removed": 10,
            "bytes_freed": 1024 * 1024,
            "directories_removed": 5,
        }

        result = await bronze_cleanup_service.cleanup()

        assert result.files_removed == 10
        assert result.bytes_freed == 1024 * 1024
        assert result.directories_removed == 5
        assert result.dry_run is False

        # Verify storage was called with correct cutoff date (approximately)
        mock_storage.cleanup_bronze.assert_called_once()
        call_args = mock_storage.cleanup_bronze.call_args
        cutoff_date = call_args.kwargs["cutoff_date"]
        expected_cutoff = datetime(2026, 1, 24, 12, 0, tzinfo=UTC)
        assert cutoff_date == expected_cutoff

    @pytest.mark.asyncio
    async def test_cleanup_with_custom_retention(
        self, bronze_cleanup_service, mock_storage
    ):
        """Test cleanup with custom retention period."""
        mock_storage.cleanup_bronze.return_value = {
            "files_removed": 5,
            "bytes_freed": 512 * 1024,
            "directories_removed": 2,
        }

        result = await bronze_cleanup_service.cleanup(retention_days=30)

        assert result.files_removed == 5

        # Verify correct retention was used
        call_args = mock_storage.cleanup_bronze.call_args
        cutoff_date = call_args.kwargs["cutoff_date"]
        expected_cutoff = datetime(2026, 3, 25, 12, 0, tzinfo=UTC)
        assert cutoff_date == expected_cutoff

    @pytest.mark.asyncio
    async def test_cleanup_dry_run(self, bronze_cleanup_service, mock_storage):
        """Test cleanup in dry run mode."""
        mock_storage.cleanup_bronze.return_value = {
            "files_removed": 10,
            "bytes_freed": 1024 * 1024,
            "directories_removed": 5,
        }

        result = await bronze_cleanup_service.cleanup(dry_run=True)

        assert result.dry_run is True
        mock_storage.cleanup_bronze.assert_called_once()
        call_args = mock_storage.cleanup_bronze.call_args
        assert call_args.kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_cleanup_no_files(self, bronze_cleanup_service, mock_storage):
        """Test cleanup when no files to remove."""
        mock_storage.cleanup_bronze.return_value = {
            "files_removed": 0,
            "bytes_freed": 0,
            "directories_removed": 0,
        }

        result = await bronze_cleanup_service.cleanup()

        assert result.files_removed == 0
        assert result.bytes_freed == 0
        assert result.directories_removed == 0


@pytest.mark.unit
class TestBronzeCleanupServiceFormatBytes:
    """Test BronzeCleanupService.format_bytes static method."""

    def test_format_bytes_gb(self):
        """Test formatting bytes in GB."""
        result = BronzeCleanupService.format_bytes(2 * 1024**3)
        assert result == "2.00 GB"

    def test_format_bytes_mb(self):
        """Test formatting bytes in MB."""
        result = BronzeCleanupService.format_bytes(500 * 1024**2)
        assert result == "500.00 MB"

    def test_format_bytes_kb(self):
        """Test formatting bytes in KB."""
        result = BronzeCleanupService.format_bytes(100 * 1024)
        assert result == "100.00 KB"

    def test_format_bytes_small(self):
        """Test formatting small byte values."""
        result = BronzeCleanupService.format_bytes(512)
        assert result == "512 bytes"

    def test_format_bytes_zero(self):
        """Test formatting zero bytes."""
        result = BronzeCleanupService.format_bytes(0)
        assert result == "0 bytes"
