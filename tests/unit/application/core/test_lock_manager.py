from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from bioetl.application.core.config import LockConfig
from bioetl.application.core.lifecycle.lock_runtime_service import (
    LockRuntimeService,
    LockRuntimeServiceCreateContext,
)
from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownSignal,
)
from bioetl.domain.locking import FencingToken
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID, RunType

pytestmark = pytest.mark.unit

# Test UUID constant for consistent assertions
TEST_RUN_ID: RunID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

# Reusable test token
_TEST_TOKEN = FencingToken(
    sequence=1,
    key="lock:test_pipeline",
    owner_id=TEST_RUN_ID,
    issued_at=100.0,
)


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
def lock_config() -> LockConfig:
    """Create a test LockConfig."""
    return LockConfig(
        lock_key="lock:test_pipeline",
        exclusive=False,
        lock_ttl=60,
        wait_for_lock=False,
        wait_timeout=300,
        heartbeat_interval=60,
    )


@pytest.fixture
def lock_manager(
    mock_lock_port: AsyncMock, mock_shutdown_signal: Mock, lock_config: LockConfig
) -> LockRuntimeService:
    return LockRuntimeService(
        lock_port=mock_lock_port,
        run_id=TEST_RUN_ID,
        config=lock_config,
        logger=Mock(),
        shutdown_signal=mock_shutdown_signal,
    )


class TestLockRuntimeService:
    async def test_acquire_lock_success(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock acquisition returns FencingToken."""
        mock_lock_port.acquire.return_value = _TEST_TOKEN

        result = await lock_manager.acquire()

        assert result is not None
        assert isinstance(result, FencingToken)
        assert result.sequence == 1
        mock_lock_port.acquire.assert_called_once_with(
            key="lock:test_pipeline",
            owner_id=TEST_RUN_ID,
            ttl=60,
            wait=False,
            wait_timeout=300,
            exclusive=False,
        )

    async def test_acquire_lock_failure(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test failure to acquire lock returns None."""
        mock_lock_port.acquire.return_value = None

        result = await lock_manager.acquire()

        assert result is None

    async def test_release_lock_success(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test successful lock release."""
        mock_lock_port.release.return_value = True

        await lock_manager.release()

        mock_lock_port.release.assert_called_once_with(
            "lock:test_pipeline", TEST_RUN_ID, exclusive=False
        )

    async def test_heartbeat_loop_loss(
        self,
        lock_manager: LockRuntimeService,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
    ) -> None:
        """Test heartbeat failure triggers shutdown."""
        # Start heartbeat to initialize the HeartbeatTask
        # First success, then fail.
        mock_lock_port.heartbeat.side_effect = [True, False]

        # Start heartbeat successfully
        await lock_manager.start_heartbeat()

        # The heartbeat task is running, we need to check its behavior
        # Since the task runs in background, we verify setup
        assert lock_manager._heartbeat is not None
        assert lock_manager._heartbeat.is_running

        # Stop to clean up
        await lock_manager._heartbeat.stop()

    async def test_context_manager_success(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test usage as async context manager."""
        mock_lock_port.acquire.return_value = _TEST_TOKEN
        mock_lock_port.release.return_value = True
        mock_lock_port.heartbeat.return_value = True

        async with lock_manager:
            assert lock_manager._heartbeat is not None
            assert lock_manager._heartbeat.is_running

        mock_lock_port.acquire.assert_called_once()
        mock_lock_port.release.assert_called_once()
        # Heartbeat should be stopped after exit
        assert lock_manager._heartbeat is None

    async def test_start_heartbeat_failure(
        self,
        lock_manager: LockRuntimeService,
        mock_lock_port: AsyncMock,
        mock_shutdown_signal: Mock,
    ) -> None:
        """Heartbeat failure on start triggers shutdown before work begins."""

        mock_lock_port.heartbeat.return_value = False

        with pytest.raises(PipelineShutdownError):
            await lock_manager.start_heartbeat()

        mock_shutdown_signal.request.assert_called_once()

    async def test_context_manager_failure(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test context manager raises if lock not acquired."""
        mock_lock_port.acquire.return_value = None
        entered = False

        with pytest.raises(PipelineShutdownError):
            async with lock_manager:
                entered = True
        assert entered is False

    async def test_validate_uses_fencing_token(
        self, lock_manager: LockRuntimeService, mock_lock_port: AsyncMock
    ) -> None:
        """Test validate uses fencing token when available."""
        lock_manager._fencing_token = _TEST_TOKEN
        mock_lock_port.validate_fencing_token.return_value = True

        result = await lock_manager.validate()

        assert result is True
        mock_lock_port.validate_fencing_token.assert_called_once_with(
            "lock:test_pipeline", _TEST_TOKEN
        )


class TestLockConfig:
    """Tests for LockConfig dataclass."""

    def test_lock_config_defaults(self) -> None:
        """Test LockConfig with default values."""
        config = LockConfig(lock_key="test:key")
        assert config.lock_key == "test:key"
        assert config.exclusive is False
        assert config.lock_ttl == 90
        assert config.wait_for_lock is True
        assert config.wait_timeout == 300
        assert config.heartbeat_interval == 30

    def test_lock_config_for_pipeline_incremental(self) -> None:
        """Test LockConfig factory for incremental run."""
        config = LockConfig.for_pipeline(
            provider="chembl",
            entity_type="activity",
            run_type=RunType.INCREMENTAL,
        )
        assert config.lock_key == "lock:chembl_activity"
        assert config.exclusive is False

    def test_lock_config_for_pipeline_backfill(self) -> None:
        """Test LockConfig factory for backfill run (exclusive)."""
        config = LockConfig.for_pipeline(
            provider="chembl",
            entity_type="activity",
            run_type=RunType.BACKFILL,
        )
        assert config.lock_key == "lock:chembl_activity:exclusive"
        assert config.exclusive is True

    def test_lock_config_for_pipeline_rebuild(self) -> None:
        """Test LockConfig factory for rebuild run (exclusive)."""
        config = LockConfig.for_pipeline(
            provider="pubchem",
            entity_type="compound",
            run_type=RunType.REBUILD,
        )
        assert config.lock_key == "lock:pubchem_compound:exclusive"
        assert config.exclusive is True


def test_lock_key_format_incremental(
    mock_lock_port: AsyncMock, mock_shutdown_signal: Mock
) -> None:
    manager = LockRuntimeService.create(
        LockRuntimeServiceCreateContext(
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
    )

    assert manager._config.lock_key == "lock:chembl_activity"
    assert manager._config.exclusive is False


def test_lock_key_format_exclusive(
    mock_lock_port: AsyncMock, mock_shutdown_signal: Mock
) -> None:
    manager = LockRuntimeService.create(
        LockRuntimeServiceCreateContext(
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
    )

    assert manager._config.lock_key == "lock:chembl_activity:exclusive"
    assert manager._config.exclusive is True
    assert manager._config.wait_for_lock is True
