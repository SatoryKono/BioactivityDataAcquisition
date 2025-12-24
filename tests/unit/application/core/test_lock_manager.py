from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID, RunType

# Test UUID constant for consistent assertions
TEST_RUN_ID: RunID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture
def mock_lock_port() -> AsyncMock:
    return AsyncMock(spec=LockPort)


@pytest.fixture
def mock_shutdown_signal() -> Mock:
    signal = Mock(spec=ShutdownSignal)
    signal.is_requested = False
    signal.request = Mock()
    return signal


@pytest.fixture
def lock_manager(mock_lock_port: AsyncMock, mock_shutdown_signal: Mock) -> LockManager:
    return LockManager(
        lock_port=mock_lock_port,
        run_id=TEST_RUN_ID,
        lock_key="lock:test_pipeline",
        exclusive=False,
        lock_ttl=60,
        wait_for_lock=False,
        wait_timeout=300,
        heartbeat_interval=60,
        logger=Mock(),
        shutdown_signal=mock_shutdown_signal,
    )


class TestLockManager:
    async def test_acquire_lock_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock acquisition."""
        mock_lock_port.acquire.return_value = True

        await lock_manager.acquire()

        mock_lock_port.acquire.assert_called_once_with(
            key="lock:test_pipeline",
            owner_id=str(TEST_RUN_ID),
            ttl=60,
            wait=False,
            wait_timeout=300,
            exclusive=False,
        )

    async def test_acquire_lock_failure(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test failure to acquire lock returns False."""
        mock_lock_port.acquire.return_value = False

        result = await lock_manager.acquire()

        assert result is False

    async def test_release_lock_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock release."""
        mock_lock_port.release.return_value = True

        await lock_manager.release()

        mock_lock_port.release.assert_called_once_with(
            "lock:test_pipeline", str(TEST_RUN_ID), exclusive=False
        )

    async def test_heartbeat_loop_loss(
        self,
        lock_manager: LockManager,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
    ) -> None:
        """Test heartbeat failure triggers shutdown."""
        # Setup heartbeat failure
        mock_lock_port.heartbeat.return_value = False

        # Test the loop directly by mocking sleep to control execution
        with patch("asyncio.sleep", new_callable=AsyncMock):
            # We need sleep to run once then stop loop or raise error
            # But the loop condition is !shutdown.is_requested
            # So the first iteration will:
            # 1. sleep
            # 2. heartbeat -> returns False
            # 3. logs error, requests shutdown, raises PipelineShutdownError

            with pytest.raises(PipelineShutdownError):
                await lock_manager._heartbeat_loop()

        assert mock_shutdown_signal.request.called

    async def test_context_manager_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test usage as async context manager."""
        mock_lock_port.acquire.return_value = True
        mock_lock_port.release.return_value = True
        mock_lock_port.heartbeat.return_value = True

        async with lock_manager:
            assert lock_manager._heartbeat_task is not None

        mock_lock_port.acquire.assert_called_once()
        mock_lock_port.release.assert_called_once()
        # Task should be cancelled/done
        assert (
            lock_manager._heartbeat_task.done()
            or lock_manager._heartbeat_task.cancelled()
        )

    async def test_start_heartbeat_failure(
        self,
        lock_manager: LockManager,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
    ) -> None:
        """Heartbeat failure on start triggers shutdown before work begins."""

        mock_lock_port.heartbeat.return_value = False

        with pytest.raises(PipelineShutdownError):
            await lock_manager.start_heartbeat()

        mock_shutdown_signal.request.assert_called_once()

    async def test_context_manager_failure(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test context manager raises if lock not acquired."""
        mock_lock_port.acquire.return_value = False

        with pytest.raises(PipelineShutdownError):
            async with lock_manager:
                pass


def test_lock_key_format_incremental(
    mock_lock_port: AsyncMock, mock_shutdown_signal: Mock
) -> None:
    manager = LockManager.create(
        lock_port=mock_lock_port,
        run_id=TEST_RUN_ID,
        provider="chembl",
        entity_type="activity",
        run_type=RunType.INCREMENTAL,
        lock_ttl=60,
        wait_for_lock=False,
        wait_timeout=300,
        heartbeat_interval=20,
        logger=Mock(),
        shutdown_signal=mock_shutdown_signal,
    )

    assert manager._lock_key == "lock:chembl_activity"
    assert manager._exclusive is False


def test_lock_key_format_exclusive(
    mock_lock_port: AsyncMock, mock_shutdown_signal: Mock
) -> None:
    manager = LockManager.create(
        lock_port=mock_lock_port,
        run_id=TEST_RUN_ID,
        provider="chembl",
        entity_type="activity",
        run_type=RunType.BACKFILL,
        lock_ttl=60,
        wait_for_lock=True,
        wait_timeout=120,
        heartbeat_interval=20,
        logger=Mock(),
        shutdown_signal=mock_shutdown_signal,
    )

    assert manager._lock_key == "lock:chembl_activity:exclusive"
    assert manager._exclusive is True
    assert manager._wait_for_lock is True
