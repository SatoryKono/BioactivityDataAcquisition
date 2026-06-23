"""Unit tests for PostrunCleanupService.

Tests cleanup orchestration logic: tracer close, error handling,
warning-mode fallback, None tracer handling.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.postrun.cleanup_orchestrator import PostrunCleanupService


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_tracer() -> MagicMock:
    """Create a mock tracer port."""
    tracer = MagicMock()
    tracer.close = MagicMock()
    return tracer


@pytest.fixture
def cleanup_service(mock_logger: MagicMock) -> PostrunCleanupService:
    """Create PostrunCleanupService with RuntimeError in warning_allowlist."""
    return PostrunCleanupService(
        logger=mock_logger,
        warning_allowlist=(RuntimeError, OSError),
    )


@pytest.mark.unit
class TestPostrunCleanupServiceInit:
    """Tests for PostrunCleanupService initialization."""

    def test_initialization_stores_logger(self, mock_logger: MagicMock) -> None:
        """Test that logger is stored on construction."""
        service = PostrunCleanupService(
            logger=mock_logger,
            warning_allowlist=(RuntimeError,),
        )
        assert service._logger is mock_logger

    def test_initialization_stores_warning_allowlist(
        self, mock_logger: MagicMock
    ) -> None:
        """Test that warning_allowlist is stored on construction."""
        allowlist = (RuntimeError, OSError, ValueError)
        service = PostrunCleanupService(
            logger=mock_logger,
            warning_allowlist=allowlist,
        )
        assert service._warning_allowlist == allowlist

    def test_initialization_with_empty_allowlist(self, mock_logger: MagicMock) -> None:
        """Test initialization with empty warning_allowlist tuple."""
        service = PostrunCleanupService(
            logger=mock_logger,
            warning_allowlist=(),
        )
        assert service._warning_allowlist == ()


@pytest.mark.unit
class TestCleanupTracerSuccess:
    """Tests for successful tracer cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_tracer_calls_close(
        self, cleanup_service: PostrunCleanupService, mock_tracer: MagicMock
    ) -> None:
        """Test that cleanup_tracer calls tracer.close()."""
        await cleanup_service.cleanup_tracer(mock_tracer)

        mock_tracer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_tracer_logs_debug_on_success(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that a debug log is emitted when tracer closes successfully."""
        await cleanup_service.cleanup_tracer(mock_tracer)

        mock_logger.debug.assert_called_once_with("Tracer closed successfully")

    @pytest.mark.asyncio
    async def test_cleanup_tracer_none_skips_close(
        self, cleanup_service: PostrunCleanupService
    ) -> None:
        """Test that cleanup_tracer with None tracer is a no-op."""
        # Must not raise, must not call anything
        await cleanup_service.cleanup_tracer(None)

    @pytest.mark.asyncio
    async def test_cleanup_tracer_none_does_not_log_debug(
        self,
        cleanup_service: PostrunCleanupService,
        mock_logger: MagicMock,
    ) -> None:
        """Test that no debug log is emitted for None tracer."""
        await cleanup_service.cleanup_tracer(None)

        mock_logger.debug.assert_not_called()


@pytest.mark.unit
class TestCleanupTracerFailureHandling:
    """Tests for tracer cleanup failure and warning-mode fallback."""

    @pytest.mark.asyncio
    async def test_cleanup_tracer_warning_on_allowlisted_error(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that allowlisted error emits a warning instead of raising."""
        mock_tracer.close.side_effect = RuntimeError("connection lost")

        # Must not raise
        await cleanup_service.cleanup_tracer(mock_tracer)

        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_tracer_warning_contains_error_info(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that warning log contains error details."""
        mock_tracer.close.side_effect = RuntimeError("connection lost")

        await cleanup_service.cleanup_tracer(mock_tracer)

        call_kwargs = mock_logger.warning.call_args[1]
        assert "error" in call_kwargs
        assert "error_type" in call_kwargs
        assert "reason_code" in call_kwargs
        assert call_kwargs["reason_code"] == "POSTRUN_TRACER_CLOSE_FAILED"

    @pytest.mark.asyncio
    async def test_cleanup_tracer_os_error_in_allowlist(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that OSError (also in allowlist) is treated as warning."""
        mock_tracer.close.side_effect = OSError("fd closed")

        await cleanup_service.cleanup_tracer(mock_tracer)

        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_tracer_raises_non_allowlisted_error(
        self, mock_logger: MagicMock, mock_tracer: MagicMock
    ) -> None:
        """Test that non-allowlisted errors propagate (not swallowed)."""
        service = PostrunCleanupService(
            logger=mock_logger,
            warning_allowlist=(OSError,),  # RuntimeError NOT in allowlist
        )
        mock_tracer.close.side_effect = RuntimeError("unexpected crash")

        with pytest.raises(RuntimeError, match="unexpected crash"):
            await service.cleanup_tracer(mock_tracer)

    @pytest.mark.asyncio
    async def test_cleanup_tracer_warning_includes_reason(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that warning log includes reason field."""
        mock_tracer.close.side_effect = RuntimeError("shutdown error")

        await cleanup_service.cleanup_tracer(mock_tracer)

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs.get("reason") == "tracer_close_failed"

    @pytest.mark.asyncio
    async def test_cleanup_tracer_warning_error_type_name(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that warning log includes correct error_type name."""
        mock_tracer.close.side_effect = RuntimeError("boom")

        await cleanup_service.cleanup_tracer(mock_tracer)

        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_cleanup_tracer_does_not_log_debug_on_error(
        self,
        cleanup_service: PostrunCleanupService,
        mock_tracer: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that debug success log is NOT emitted when close raises."""
        mock_tracer.close.side_effect = RuntimeError("oops")

        await cleanup_service.cleanup_tracer(mock_tracer)

        mock_logger.debug.assert_not_called()
