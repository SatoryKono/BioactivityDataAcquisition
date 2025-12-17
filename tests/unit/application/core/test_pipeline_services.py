"""Unit tests for PipelineServices."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.pipeline_services import PipelineServices


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    mock_logger = MagicMock()
    mock_data_source = AsyncMock()
    mock_data_source.__aenter__ = AsyncMock(return_value=mock_data_source)
    mock_data_source.__aexit__ = AsyncMock()
    mock_data_source.aclose = AsyncMock()

    mock_storage = AsyncMock()
    mock_storage.aclose = AsyncMock()

    mock_lock = AsyncMock()
    mock_lock.aclose = AsyncMock()

    mock_checkpoint = AsyncMock()
    mock_checkpoint.aclose = AsyncMock()

    mock_quarantine = AsyncMock()
    mock_quarantine.aclose = AsyncMock()

    mock_metrics = MagicMock()

    return PipelineServices(
        data_source=mock_data_source,
        storage=mock_storage,
        lock=mock_lock,
        checkpoint=mock_checkpoint,
        quarantine=mock_quarantine,
        metrics=mock_metrics,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPipelineServicesInit:
    """Tests for PipelineServices initialization."""

    def test_init_stores_all_services(self, mock_services):
        """Test that initialization stores all services."""
        assert mock_services.data_source is not None
        assert mock_services.storage is not None
        assert mock_services.lock is not None
        assert mock_services.checkpoint is not None
        assert mock_services.quarantine is not None
        assert mock_services.metrics is not None
        assert mock_services.logger is not None

    def test_is_frozen(self, mock_services):
        """Test that services cannot be modified after creation."""
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            mock_services.data_source = AsyncMock()


@pytest.mark.unit
class TestPipelineServicesContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_aenter_initializes_data_source(self, mock_services):
        """Test that __aenter__ initializes the data source."""
        result = await mock_services.__aenter__()

        assert result is mock_services
        mock_services.data_source.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_aexit_calls_aclose(self, mock_services):
        """Test that __aexit__ calls aclose."""
        await mock_services.__aexit__(None, None, None)

        mock_services.data_source.aclose.assert_called_once()
        mock_services.storage.aclose.assert_called_once()
        mock_services.lock.aclose.assert_called_once()
        mock_services.checkpoint.aclose.assert_called_once()
        mock_services.quarantine.aclose.assert_called_once()


@pytest.mark.unit
class TestPipelineServicesAclose:
    """Tests for aclose method."""

    @pytest.mark.asyncio
    async def test_aclose_closes_all_services(self, mock_services):
        """Test that aclose closes all services."""
        await mock_services.aclose()

        mock_services.data_source.aclose.assert_called_once()
        mock_services.storage.aclose.assert_called_once()
        mock_services.lock.aclose.assert_called_once()
        mock_services.checkpoint.aclose.assert_called_once()
        mock_services.quarantine.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_logs_info(self, mock_services):
        """Test that aclose logs info messages."""
        await mock_services.aclose()

        # Should log start and end messages
        assert mock_services.logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_aclose_handles_service_errors(self, mock_services):
        """Test that aclose handles errors from services."""
        # Make one service raise an error
        mock_services.storage.aclose.side_effect = RuntimeError("Storage error")

        # Should not raise, but should log error
        await mock_services.aclose()

        mock_services.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_continues_after_error(self, mock_services):
        """Test that aclose continues closing services after error."""
        # Make first service raise an error
        mock_services.data_source.aclose.side_effect = RuntimeError("Data source error")

        await mock_services.aclose()

        # All other services should still be closed
        mock_services.storage.aclose.assert_called_once()
        mock_services.lock.aclose.assert_called_once()
        mock_services.checkpoint.aclose.assert_called_once()
        mock_services.quarantine.aclose.assert_called_once()
