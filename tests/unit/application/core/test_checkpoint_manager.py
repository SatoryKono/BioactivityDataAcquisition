"""Unit tests for CheckpointManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager


@pytest.fixture
def mock_checkpoint_port():
    """Create mock checkpoint port."""
    port = AsyncMock()
    port.load = AsyncMock(return_value=None)
    port.save = AsyncMock()
    port.delete = AsyncMock()
    return port


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def checkpoint_manager(mock_checkpoint_port, mock_logger):
    """Create CheckpointManager instance."""
    run_id = uuid4()
    return CheckpointManager(
        checkpoint_port=mock_checkpoint_port,
        logger=mock_logger,
        pipeline_name="test_pipeline",
        run_id=run_id,
        resume=True,
    )


@pytest.mark.unit
class TestCheckpointManagerInit:
    """Tests for CheckpointManager initialization."""

    def test_init_with_all_params(self, mock_checkpoint_port, mock_logger):
        """Test initialization with all parameters."""
        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="my_pipeline",
            run_id=run_id,
            resume=False,
        )

        assert manager._pipeline_name == "my_pipeline"
        assert manager._run_id == run_id
        assert manager._resume is False


@pytest.mark.unit
class TestCheckpointManagerLoadCheckpoint:
    """Tests for CheckpointManager.load_checkpoint method."""

    async def test_load_checkpoint_when_resume_true_and_exists(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint when resuming and checkpoint exists."""
        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
        )

        result = await manager.load_checkpoint()

        assert result is not None
        mock_checkpoint_port.load.assert_called_once_with("test_pipeline")
        mock_logger.info.assert_called()

    async def test_load_checkpoint_when_resume_true_but_no_checkpoint(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint when resuming but no checkpoint exists."""
        mock_checkpoint_port.load.return_value = None

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_called_once()

    async def test_load_checkpoint_when_resume_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint when not resuming."""
        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=False,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_not_called()


@pytest.mark.unit
class TestCheckpointManagerSaveCheckpoint:
    """Tests for CheckpointManager.save_checkpoint method."""

    async def test_save_checkpoint_saves_metadata(
        self, checkpoint_manager, mock_checkpoint_port
    ):
        """Test save_checkpoint saves metadata correctly."""
        await checkpoint_manager.save_checkpoint(records_processed=500)

        mock_checkpoint_port.save.assert_called_once()
        call_kwargs = mock_checkpoint_port.save.call_args.kwargs
        assert call_kwargs["pipeline"] == "test_pipeline"
        assert call_kwargs["metadata"] == {"records_processed": 500}


@pytest.mark.unit
class TestCheckpointManagerDeleteCheckpoint:
    """Tests for CheckpointManager.delete_checkpoint method."""

    async def test_delete_checkpoint(self, checkpoint_manager, mock_checkpoint_port):
        """Test delete_checkpoint calls port.delete."""
        await checkpoint_manager.delete_checkpoint()

        mock_checkpoint_port.delete.assert_called_once_with("test_pipeline")
