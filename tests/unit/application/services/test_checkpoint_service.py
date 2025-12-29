"""Unit tests for CheckpointService.

Tests the checkpoint administrative service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.services.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
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
def mock_checkpoint_port():
    """Create a mock checkpoint port."""
    port = MagicMock()
    port.list_all = AsyncMock(return_value=[])
    port.load = AsyncMock(return_value=None)
    port.delete = AsyncMock()
    port.aclose = AsyncMock()
    return port


@pytest.fixture
def checkpoint_service(mock_checkpoint_port, mock_logger):
    """Create a CheckpointService instance."""
    return CheckpointService(
        checkpoint_port=mock_checkpoint_port,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestCheckpointInfo:
    """Test CheckpointInfo dataclass."""

    def test_checkpoint_info_creation(self):
        """Test CheckpointInfo can be created."""
        info = CheckpointInfo(
            pipeline_name="test_pipeline",
            run_id="12345",
            metadata={"records_processed": 100},
        )

        assert info.pipeline_name == "test_pipeline"
        assert info.run_id == "12345"
        assert info.metadata == {"records_processed": 100}

    def test_checkpoint_info_with_none_run_id(self):
        """Test CheckpointInfo with None run_id."""
        info = CheckpointInfo(
            pipeline_name="test_pipeline",
            run_id=None,
            metadata={},
        )

        assert info.run_id is None


@pytest.mark.unit
class TestCheckpointServiceListCheckpoints:
    """Test CheckpointService.list_checkpoints method."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty(self, checkpoint_service, mock_checkpoint_port):
        """Test listing checkpoints when none exist."""
        mock_checkpoint_port.list_all.return_value = []

        result = await checkpoint_service.list_checkpoints()

        assert result == []
        mock_checkpoint_port.list_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_data(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test listing checkpoints with existing data."""
        run_id = uuid4()
        mock_checkpoint_port.list_all.return_value = ["pipeline1", "pipeline2"]
        mock_checkpoint_port.load.side_effect = [
            (run_id, {"records_processed": 100}),
            (run_id, {"records_processed": 200}),
        ]

        result = await checkpoint_service.list_checkpoints()

        assert len(result) == 2
        assert result[0].pipeline_name == "pipeline1"
        assert result[0].metadata == {"records_processed": 100}
        assert result[1].pipeline_name == "pipeline2"
        assert result[1].metadata == {"records_processed": 200}

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_unloadable(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test listing checkpoints when some can't be loaded."""
        run_id = uuid4()
        mock_checkpoint_port.list_all.return_value = ["pipeline1", "pipeline2"]
        mock_checkpoint_port.load.side_effect = [
            (run_id, {"records_processed": 100}),
            None,  # Pipeline2 checkpoint can't be loaded
        ]

        result = await checkpoint_service.list_checkpoints()

        assert len(result) == 2
        assert result[0].run_id == str(run_id)
        assert result[1].run_id is None
        assert result[1].metadata == {}


@pytest.mark.unit
class TestCheckpointServiceGetCheckpoint:
    """Test CheckpointService.get_checkpoint method."""

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test getting a checkpoint that doesn't exist."""
        mock_checkpoint_port.load.return_value = None

        result = await checkpoint_service.get_checkpoint("nonexistent")

        assert result is None
        mock_checkpoint_port.load.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test getting an existing checkpoint."""
        run_id = uuid4()
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})

        result = await checkpoint_service.get_checkpoint("pipeline1")

        assert result is not None
        assert result.pipeline_name == "pipeline1"
        assert result.run_id == str(run_id)
        assert result.metadata == {"records_processed": 100}


@pytest.mark.unit
class TestCheckpointServiceDeleteCheckpoint:
    """Test CheckpointService.delete_checkpoint method."""

    @pytest.mark.asyncio
    async def test_delete_checkpoint_not_found(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test deleting a checkpoint that doesn't exist."""
        mock_checkpoint_port.load.return_value = None

        result = await checkpoint_service.delete_checkpoint("nonexistent")

        assert result is False
        mock_checkpoint_port.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_checkpoint_success(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test successfully deleting a checkpoint."""
        run_id = uuid4()
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})

        result = await checkpoint_service.delete_checkpoint("pipeline1")

        assert result is True
        mock_checkpoint_port.delete.assert_called_once_with("pipeline1")


@pytest.mark.unit
class TestCheckpointServiceAclose:
    """Test CheckpointService.aclose method."""

    @pytest.mark.asyncio
    async def test_aclose(self, checkpoint_service, mock_checkpoint_port):
        """Test closing the service."""
        await checkpoint_service.aclose()

        mock_checkpoint_port.aclose.assert_called_once()
