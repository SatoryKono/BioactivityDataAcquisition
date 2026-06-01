"""Tests for HeartbeatTask component.

Tests the extracted heartbeat management functionality from LockRuntimeService.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from bioetl.application.core.lifecycle.heartbeat import HeartbeatTask
from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownSignal,
)
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit

# Test UUID constant for consistent assertions
TEST_RUN_ID: RunID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def mock_lock_port() -> AsyncMock:
    """Create mock lock port."""
    return AsyncMock(spec=LockPort)


@pytest.fixture
def mock_shutdown_signal() -> Mock:
    """Create mock shutdown signal."""
    signal = Mock(spec=ShutdownSignal)
    signal.is_requested = False
    signal.request = Mock()
    return signal


@pytest.fixture
def mock_logger() -> Mock:
    """Create mock logger."""
    logger = Mock()
    logger.error = Mock()
    logger.info = Mock()
    return logger


@pytest.fixture
def heartbeat_task(
    mock_lock_port: AsyncMock,
    mock_shutdown_signal: Mock,
    mock_logger: Mock,
) -> HeartbeatTask:
    """Create HeartbeatTask instance."""
    return HeartbeatTask(
        lock_port=mock_lock_port,
        lock_key="lock:test_pipeline",
        owner_id=TEST_RUN_ID,
        exclusive=False,
        interval=1,  # 1 second for faster tests
        shutdown_signal=mock_shutdown_signal,
        logger=mock_logger,
    )


class TestHeartbeatTask:
    """Tests for HeartbeatTask."""

    async def test_start_success(
        self,
        heartbeat_task: HeartbeatTask,
        mock_lock_port: AsyncMock,
    ) -> None:
        """Test successful heartbeat start."""
        mock_lock_port.heartbeat.return_value = True

        await heartbeat_task.start()

        assert heartbeat_task.is_running
        mock_lock_port.heartbeat.assert_called_once_with(
            "lock:test_pipeline", TEST_RUN_ID, exclusive=False
        )

        # Clean up
        await heartbeat_task.stop()

    async def test_start_failure_triggers_shutdown(
        self,
        heartbeat_task: HeartbeatTask,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
    ) -> None:
        """Test that heartbeat failure on start triggers shutdown."""
        mock_lock_port.heartbeat.return_value = False

        with pytest.raises(PipelineShutdownError):
            await heartbeat_task.start()

        mock_shutdown_signal.request.assert_called_once()
        assert not heartbeat_task.is_running

    async def test_stop_cancels_task(
        self,
        heartbeat_task: HeartbeatTask,
        mock_lock_port: AsyncMock,
    ) -> None:
        """Test that stop cancels the background task."""
        mock_lock_port.heartbeat.return_value = True

        await heartbeat_task.start()
        assert heartbeat_task.is_running

        await heartbeat_task.stop()
        assert not heartbeat_task.is_running

    async def test_stop_idempotent(
        self,
        heartbeat_task: HeartbeatTask,
    ) -> None:
        """Test that stop is idempotent (safe to call multiple times)."""
        # Stop without starting should not raise
        await heartbeat_task.stop()
        await heartbeat_task.stop()

        assert not heartbeat_task.is_running

    async def test_is_running_property(
        self,
        heartbeat_task: HeartbeatTask,
        mock_lock_port: AsyncMock,
    ) -> None:
        """Test is_running property reflects task state."""
        mock_lock_port.heartbeat.return_value = True

        assert not heartbeat_task.is_running

        await heartbeat_task.start()
        assert heartbeat_task.is_running

        await heartbeat_task.stop()
        assert not heartbeat_task.is_running

    async def test_heartbeat_loop_runs_periodically(
        self,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
        mock_logger: Mock,
    ) -> None:
        """Test that heartbeat loop calls lock_port periodically."""
        second_heartbeat = asyncio.Event()
        call_count = 0

        async def heartbeat(*args: object, **kwargs: object) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                second_heartbeat.set()
            return True

        mock_lock_port.heartbeat.side_effect = heartbeat
        heartbeat_task = HeartbeatTask(
            lock_port=mock_lock_port,
            lock_key="lock:test_pipeline",
            owner_id=TEST_RUN_ID,
            exclusive=False,
            interval=0,
            shutdown_signal=mock_shutdown_signal,
            logger=mock_logger,
        )

        await heartbeat_task.start()
        await asyncio.wait_for(second_heartbeat.wait(), timeout=1.0)

        await heartbeat_task.stop()

        assert mock_lock_port.heartbeat.call_count >= 2

    async def test_exclusive_flag_passed_to_heartbeat(
        self,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
        mock_logger: Mock,
    ) -> None:
        """Test that exclusive flag is passed to heartbeat calls."""
        task = HeartbeatTask(
            lock_port=mock_lock_port,
            lock_key="lock:test_pipeline:exclusive",
            owner_id=TEST_RUN_ID,
            exclusive=True,
            interval=1,
            shutdown_signal=mock_shutdown_signal,
            logger=mock_logger,
        )

        mock_lock_port.heartbeat.return_value = True

        await task.start()
        await task.stop()

        mock_lock_port.heartbeat.assert_called_with(
            "lock:test_pipeline:exclusive", TEST_RUN_ID, exclusive=True
        )
