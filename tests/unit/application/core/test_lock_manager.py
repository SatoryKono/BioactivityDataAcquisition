from unittest.mock import AsyncMock, Mock, patch

import pytest

from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.shutdown import ShutdownSignal, PipelineShutdownError
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID


@pytest.fixture
def mock_lock_port() -> AsyncMock:
    return AsyncMock(spec=LockPort)


@pytest.fixture
def mock_shutdown_signal() -> Mock:
    signal = Mock(spec=ShutdownSignal)
    signal.is_requested = False
    return signal


@pytest.fixture
def lock_manager(mock_lock_port: AsyncMock, mock_shutdown_signal: Mock) -> LockManager:
    return LockManager(
        lock_port=mock_lock_port,
        run_id=RunID("run_123"),
        lock_key="lock:test_pipeline",
        exclusive=False,
        heartbeat_interval=60,
        logger=Mock(),
        shutdown_signal=mock_shutdown_signal,
    )


class TestLockManager:
    @pytest.mark.asyncio
    async def test_acquire_lock_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock acquisition."""
        mock_lock_port.acquire.return_value = True

        await lock_manager.acquire()

        mock_lock_port.acquire.assert_called_once_with(
            key="lock:test_pipeline",
            owner_id="run_123",
            wait=False,
            exclusive=False,
        )

    @pytest.mark.asyncio
    async def test_acquire_lock_failure(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test failure to acquire lock returns False."""
        mock_lock_port.acquire.return_value = False

        result = await lock_manager.acquire()

        assert result is False

    @pytest.mark.asyncio
    async def test_release_lock_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock release."""
        mock_lock_port.release.return_value = True

        await lock_manager.release()

        mock_lock_port.release.assert_called_once_with(
            "lock:test_pipeline", "run_123", exclusive=False
        )

    @pytest.mark.asyncio
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
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # We need sleep to run once then stop loop or raise error
            # But the loop condition is !shutdown.is_requested
            # So the first iteration will:
            # 1. sleep
            # 2. heartbeat -> returns False
            # 3. logs error, requests shutdown, raises PipelineShutdownError

            with pytest.raises(PipelineShutdownError):
                await lock_manager._heartbeat_loop()

        assert mock_shutdown_signal.request.called

    @pytest.mark.asyncio
    async def test_context_manager_success(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test usage as async context manager."""
        mock_lock_port.acquire.return_value = True
        mock_lock_port.release.return_value = True

        async with lock_manager:
            assert lock_manager._heartbeat_task is not None

        mock_lock_port.acquire.assert_called_once()
        mock_lock_port.release.assert_called_once()
        # Task should be cancelled/done
        assert (
            lock_manager._heartbeat_task.done()
            or lock_manager._heartbeat_task.cancelled()
        )

    @pytest.mark.asyncio
    async def test_context_manager_failure(
        self, lock_manager: LockManager, mock_lock_port: AsyncMock
    ) -> None:
        """Test context manager raises if lock not acquired."""
        mock_lock_port.acquire.return_value = False

        with pytest.raises(PipelineShutdownError):
            async with lock_manager:
                pass
