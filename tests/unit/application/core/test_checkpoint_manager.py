"""Unit tests for CheckpointManager."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.domain.types import RunID


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
def watermark_extractor():
    """Create a simple watermark extractor."""
    def extract(record):
        return record.get("timestamp", "2025-01-01")
    return extract


@pytest.fixture
def checkpoint_manager(mock_checkpoint_port, mock_logger, watermark_extractor):
    """Create CheckpointManager instance."""
    return CheckpointManager(
        checkpoint_port=mock_checkpoint_port,
        logger=mock_logger,
        pipeline_name="test_pipeline",
        run_id=RunID(uuid4()),
        resume=True,
        watermark_extractor=watermark_extractor,
    )


@pytest.mark.unit
class TestCheckpointManagerInit:
    """Tests for CheckpointManager initialization."""

    def test_init_with_all_params(
        self, mock_checkpoint_port, mock_logger, watermark_extractor
    ):
        """Test initialization with all parameters."""
        run_id = RunID(uuid4())
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="my_pipeline",
            run_id=run_id,
            resume=False,
            watermark_extractor=watermark_extractor,
        )

        assert manager._pipeline_name == "my_pipeline"
        assert manager._run_id == run_id
        assert manager._resume is False


@pytest.mark.unit
class TestCheckpointManagerLoadCheckpoint:
    """Tests for CheckpointManager.load_checkpoint method."""

    @pytest.mark.asyncio
    async def test_load_checkpoint_when_resume_true_and_exists(
        self, mock_checkpoint_port, mock_logger, watermark_extractor
    ):
        """Test load_checkpoint when resuming and checkpoint exists."""
        mock_checkpoint_port.load.return_value = (
            "2025-01-15T00:00:00Z",
            RunID(uuid4()),
            {"records_processed": 1000},
        )

        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=RunID(uuid4()),
            resume=True,
            watermark_extractor=watermark_extractor,
        )

        result = await manager.load_checkpoint()

        assert result == "2025-01-15T00:00:00Z"
        mock_checkpoint_port.load.assert_called_once_with("test_pipeline")
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_load_checkpoint_when_resume_true_but_no_checkpoint(
        self, mock_checkpoint_port, mock_logger, watermark_extractor
    ):
        """Test load_checkpoint when resuming but no checkpoint exists."""
        mock_checkpoint_port.load.return_value = None

        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=RunID(uuid4()),
            resume=True,
            watermark_extractor=watermark_extractor,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_checkpoint_when_resume_false(
        self, mock_checkpoint_port, mock_logger, watermark_extractor
    ):
        """Test load_checkpoint when not resuming."""
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=RunID(uuid4()),
            resume=False,
            watermark_extractor=watermark_extractor,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_not_called()


@pytest.mark.unit
class TestCheckpointManagerSaveCheckpoint:
    """Tests for CheckpointManager.save_checkpoint method."""

    @pytest.mark.asyncio
    async def test_save_checkpoint_extracts_watermark(
        self, checkpoint_manager, mock_checkpoint_port
    ):
        """Test save_checkpoint extracts watermark from record."""
        last_record = {"id": 123, "timestamp": "2025-01-20T12:00:00Z"}

        await checkpoint_manager.save_checkpoint(
            last_record=last_record,
            records_processed=500,
        )

        mock_checkpoint_port.save.assert_called_once()
        call_kwargs = mock_checkpoint_port.save.call_args.kwargs
        assert call_kwargs["pipeline"] == "test_pipeline"
        assert call_kwargs["watermark"] == "2025-01-20T12:00:00Z"
        assert call_kwargs["metadata"] == {"records_processed": 500}

    @pytest.mark.asyncio
    async def test_save_checkpoint_with_default_watermark(
        self, checkpoint_manager, mock_checkpoint_port
    ):
        """Test save_checkpoint uses default when timestamp missing."""
        last_record = {"id": 456}  # No timestamp

        await checkpoint_manager.save_checkpoint(
            last_record=last_record,
            records_processed=100,
        )

        call_kwargs = mock_checkpoint_port.save.call_args.kwargs
        assert call_kwargs["watermark"] == "2025-01-01"  # Default value


@pytest.mark.unit
class TestCheckpointManagerDeleteCheckpoint:
    """Tests for CheckpointManager.delete_checkpoint method."""

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, checkpoint_manager, mock_checkpoint_port):
        """Test delete_checkpoint calls port.delete."""
        await checkpoint_manager.delete_checkpoint()

        mock_checkpoint_port.delete.assert_called_once_with("test_pipeline")
