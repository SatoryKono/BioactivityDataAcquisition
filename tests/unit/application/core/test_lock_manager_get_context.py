"""Application-layer tests for LockCoordinator.get_context()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.lifecycle.lock_manager import LockCoordinator
from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock(spec=["info", "error", "warning", "debug"])


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return RunID(uuid4())


@pytest.fixture
def mock_lock_port(run_id: RunID) -> MagicMock:
    """Create mock LockPort with async methods."""
    token = FencingToken(
        sequence=1,
        key="lock:chembl_activity",
        owner_id=run_id,
        issued_at=100.0,
    )
    mock = MagicMock()
    mock.acquire = AsyncMock(return_value=token)
    mock.release = AsyncMock(return_value=True)
    mock.heartbeat = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_shutdown_signal() -> MagicMock:
    """Create mock ShutdownSignal."""
    signal = MagicMock()
    signal.is_requested = False
    return signal


def _build_lock_manager(
    *,
    mock_lock_port: MagicMock,
    mock_shutdown_signal: MagicMock,
    mock_logger: MagicMock,
    run_id: RunID,
    run_type: RunType,
) -> LockCoordinator:
    return LockCoordinator.create(
        lock_port=mock_lock_port,
        run_id=run_id,
        provider="chembl",
        entity_type="activity",
        run_type=run_type,
        lock_ttl=3600,
        wait_for_lock=False,
        wait_timeout=300,
        heartbeat_interval=60,
        logger=mock_logger,
        shutdown_signal=mock_shutdown_signal,
    )


@pytest.mark.asyncio
async def test_get_context_before_acquire(
    mock_lock_port: MagicMock,
    mock_shutdown_signal: MagicMock,
    mock_logger: MagicMock,
    run_id: RunID,
) -> None:
    await asyncio.sleep(0)
    manager = _build_lock_manager(
        mock_lock_port=mock_lock_port,
        mock_shutdown_signal=mock_shutdown_signal,
        mock_logger=mock_logger,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
    )

    assert manager.get_context() is None


@pytest.mark.asyncio
async def test_get_context_after_acquire(
    mock_lock_port: MagicMock,
    mock_shutdown_signal: MagicMock,
    mock_logger: MagicMock,
    run_id: RunID,
) -> None:
    manager = _build_lock_manager(
        mock_lock_port=mock_lock_port,
        mock_shutdown_signal=mock_shutdown_signal,
        mock_logger=mock_logger,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
    )

    await manager.acquire()
    ctx = manager.get_context()

    assert ctx is not None
    assert ctx.key == "lock:chembl_activity"
    assert ctx.owner_id == run_id
    assert ctx.exclusive is False
    assert ctx.is_valid() is True
    assert ctx.fencing_token is not None
    assert ctx.fencing_token.sequence == 1


@pytest.mark.asyncio
async def test_get_context_exclusive_lock(
    mock_lock_port: MagicMock,
    mock_shutdown_signal: MagicMock,
    mock_logger: MagicMock,
    run_id: RunID,
) -> None:
    manager = _build_lock_manager(
        mock_lock_port=mock_lock_port,
        mock_shutdown_signal=mock_shutdown_signal,
        mock_logger=mock_logger,
        run_id=run_id,
        run_type=RunType.BACKFILL,
    )

    await manager.acquire()
    ctx = manager.get_context()

    assert ctx is not None
    assert ctx.key == "lock:chembl_activity:exclusive"
    assert ctx.exclusive is True


@pytest.mark.asyncio
async def test_get_context_after_release(
    mock_lock_port: MagicMock,
    mock_shutdown_signal: MagicMock,
    mock_logger: MagicMock,
    run_id: RunID,
) -> None:
    manager = _build_lock_manager(
        mock_lock_port=mock_lock_port,
        mock_shutdown_signal=mock_shutdown_signal,
        mock_logger=mock_logger,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
    )

    await manager.acquire()
    assert manager.get_context() is not None

    await manager.release()
    assert manager.get_context() is None
