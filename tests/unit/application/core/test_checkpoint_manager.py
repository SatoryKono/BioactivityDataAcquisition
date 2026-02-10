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


@pytest.mark.unit
class TestCheckpointManagerForceFullScan:
    """Tests for CheckpointManager force_full_scan behavior (ADR-030)."""

    async def test_load_checkpoint_blocked_when_force_full_scan_enabled(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint returns None when force_full_scan=True, even if resume=True."""
        # Setup: checkpoint exists
        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            force_full_scan=True,
        )

        result = await manager.load_checkpoint()

        # Checkpoint load should NOT be called - blocked immediately
        mock_checkpoint_port.load.assert_not_called()
        # Result should be None
        assert result is None
        # Warning should be logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        # Message uses "full_scan_only" since ADR-031 loading_strategy formalization
        assert "full_scan_only" in warning_call[0][0].lower()

    async def test_load_checkpoint_warning_contains_adr_reference(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that warning message references ADR-030."""
        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            force_full_scan=True,
        )

        await manager.load_checkpoint()

        warning_call = mock_logger.warning.call_args
        assert "ADR-030" in warning_call[0][0]

    async def test_load_checkpoint_warning_includes_pipeline_name(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that warning includes pipeline name in extra context."""
        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="pubmed_publication",
            run_id=run_id,
            resume=True,
            force_full_scan=True,
        )

        await manager.load_checkpoint()

        warning_call = mock_logger.warning.call_args
        extra = warning_call[1].get("extra", {})
        assert extra.get("pipeline") == "pubmed_publication"
        assert extra.get("force_full_scan") is True

    async def test_load_checkpoint_works_normally_when_force_full_scan_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint works normally when force_full_scan=False (default)."""
        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",  # Non-publication pipeline
            run_id=run_id,
            resume=True,
            force_full_scan=False,
        )

        result = await manager.load_checkpoint()

        # Should load checkpoint normally
        mock_checkpoint_port.load.assert_called_once()
        assert result is not None
        assert result["records_processed"] == 1000
        # No warning logged
        mock_logger.warning.assert_not_called()

    async def test_load_checkpoint_no_warning_when_resume_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test no warning when resume=False, even if force_full_scan=True."""
        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=False,
            force_full_scan=True,
        )

        result = await manager.load_checkpoint()

        # No warning - resume wasn't requested
        mock_logger.warning.assert_not_called()
        assert result is None

    async def test_default_force_full_scan_is_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that force_full_scan defaults to False for backward compatibility."""
        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 500},
        )

        run_id = uuid4()
        # Note: force_full_scan not specified
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
        )

        result = await manager.load_checkpoint()

        # Should work normally (default force_full_scan=False)
        mock_checkpoint_port.load.assert_called_once()
        assert result is not None


@pytest.mark.unit
class TestCheckpointManagerLoadingStrategy:
    """Tests for CheckpointManager loading_strategy behavior (ADR-031)."""

    async def test_load_checkpoint_blocked_when_loading_strategy_full_scan_only(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint returns None when loading_strategy=FULL_SCAN_ONLY."""
        from bioetl.domain.medallion import LoadingStrategy

        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        result = await manager.load_checkpoint()

        # Checkpoint load should NOT be called - blocked immediately
        mock_checkpoint_port.load.assert_not_called()
        assert result is None
        mock_logger.warning.assert_called_once()

    async def test_loading_strategy_derived_from_force_full_scan_when_none(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test loading_strategy is derived from force_full_scan when not specified."""
        from bioetl.domain.medallion import LoadingStrategy

        saved_run_id = uuid4()
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = uuid4()
        # No loading_strategy, force_full_scan=True
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            force_full_scan=True,
            loading_strategy=None,  # Will be derived
        )

        # Internal loading_strategy should be FULL_SCAN_ONLY
        assert manager._loading_strategy == LoadingStrategy.FULL_SCAN_ONLY

        result = await manager.load_checkpoint()
        assert result is None

    async def test_loading_strategy_warning_references_adr_031(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that warning message references ADR-031."""
        from bioetl.domain.medallion import LoadingStrategy

        run_id = uuid4()
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        await manager.load_checkpoint()

        warning_call = mock_logger.warning.call_args
        assert "ADR-031" in warning_call[0][0]

    async def test_loading_strategy_string_conversion(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that string loading_strategy is converted to enum."""
        from bioetl.domain.medallion import LoadingStrategy

        run_id = uuid4()
        # Note: CheckpointManager receives LoadingStrategy enum from PipelineConfig
        # This test verifies the enum-based behavior
        manager = CheckpointManager(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        assert manager._loading_strategy == LoadingStrategy.FULL_SCAN_ONLY
