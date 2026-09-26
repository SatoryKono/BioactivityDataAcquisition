# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Application-layer tests for LockRuntimeService.get_context()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.core.lifecycle.lock_runtime_service import (
    LockRuntimeService,
    LockRuntimeServiceCreateContext,
)
from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock(spec=["info", "error", "warning", "debug"])


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return deterministic_run_uuid_from_callsite("test_lock_manager_get_context")


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
) -> LockRuntimeService:
    return LockRuntimeService.create(
        LockRuntimeServiceCreateContext(
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
