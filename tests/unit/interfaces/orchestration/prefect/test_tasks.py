"""Unit tests for Prefect tasks and flows."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.interfaces.orchestration.prefect.tasks import (
    delete_checkpoint_task,
    execute_pipeline_task,
    load_checkpoint_task,
    run_pipeline_flow,
)


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def mock_checkpoint_manager():
    """Create a mock checkpoint manager."""
    manager = AsyncMock()
    manager.load_checkpoint = AsyncMock(return_value="2025-01-15T00:00:00Z")
    manager.delete_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def mock_runner():
    """Create a mock pipeline runner."""
    runner = AsyncMock()
    runner.run = AsyncMock()
    return runner


@pytest.mark.unit
class TestExecutePipelineTask:
    """Tests for execute_pipeline_task."""

    @pytest.mark.asyncio
    async def test_calls_executor_execute(self, mock_executor):
        """Test that the task calls executor.execute."""
        await execute_pipeline_task.fn(
            executor=mock_executor,
            watermark="2025-01-01",
            limit=100,
        )

        mock_executor.execute.assert_called_once_with(
            watermark="2025-01-01",
            limit=100,
        )

    @pytest.mark.asyncio
    async def test_with_none_watermark(self, mock_executor):
        """Test with None watermark."""
        await execute_pipeline_task.fn(
            executor=mock_executor,
            watermark=None,
            limit=None,
        )

        mock_executor.execute.assert_called_once_with(
            watermark=None,
            limit=None,
        )


@pytest.mark.unit
class TestLoadCheckpointTask:
    """Tests for load_checkpoint_task."""

    @pytest.mark.asyncio
    async def test_returns_watermark(self, mock_checkpoint_manager):
        """Test that the task returns watermark from manager."""
        result = await load_checkpoint_task.fn(manager=mock_checkpoint_manager)

        assert result == "2025-01-15T00:00:00Z"
        mock_checkpoint_manager.load_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_checkpoint(self, mock_checkpoint_manager):
        """Test returns None when no checkpoint exists."""
        mock_checkpoint_manager.load_checkpoint.return_value = None

        result = await load_checkpoint_task.fn(manager=mock_checkpoint_manager)

        assert result is None


@pytest.mark.unit
class TestDeleteCheckpointTask:
    """Tests for delete_checkpoint_task."""

    @pytest.mark.asyncio
    async def test_calls_delete_checkpoint(self, mock_checkpoint_manager):
        """Test that the task calls manager.delete_checkpoint."""
        await delete_checkpoint_task.fn(manager=mock_checkpoint_manager)

        mock_checkpoint_manager.delete_checkpoint.assert_called_once()


@pytest.mark.unit
class TestRunPipelineFlow:
    """Tests for run_pipeline_flow."""

    @pytest.mark.asyncio
    async def test_calls_runner_run(self, mock_runner):
        """Test that the flow calls runner.run."""
        await run_pipeline_flow.fn(runner=mock_runner)

        mock_runner.run.assert_called_once()
