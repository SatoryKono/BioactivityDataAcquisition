"""Tests for domain locking primitives (RULES.md §3.3).

Verifies LockContext value object, LockNotHeldError exception,
and LockManager.get_context() method.

Note:
    Lock validation during writes is now performed at Application layer
    (BatchWriter) per RULES.md §4.6 Safety Guard. See test_batch_writer.py
    for those tests.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.locking import LockContext, LockNotHeldError
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
def valid_lock_context(run_id: RunID) -> LockContext:
    """Create a valid lock context for chembl_activity."""
    return LockContext.create(
        provider="chembl",
        entity="activity",
        owner_id=run_id,
        exclusive=False,
    )


@pytest.fixture
def exclusive_lock_context(run_id: RunID) -> LockContext:
    """Create an exclusive lock context for chembl_activity."""
    return LockContext.create(
        provider="chembl",
        entity="activity",
        owner_id=run_id,
        exclusive=True,
    )


class TestLockContext:
    """Tests for LockContext value object."""

    def test_create_normal_lock(self, run_id: RunID) -> None:
        """Test creating normal (non-exclusive) lock context."""
        ctx = LockContext.create(
            provider="chembl",
            entity="activity",
            owner_id=run_id,
            exclusive=False,
        )

        assert ctx.key == "lock:chembl_activity"
        assert ctx.owner_id == run_id
        assert ctx.exclusive is False
        assert ctx.acquired_at is not None

    def test_create_exclusive_lock(self, run_id: RunID) -> None:
        """Test creating exclusive lock context for backfill."""
        ctx = LockContext.create(
            provider="chembl",
            entity="activity",
            owner_id=run_id,
            exclusive=True,
        )

        assert ctx.key == "lock:chembl_activity:exclusive"
        assert ctx.exclusive is True

    def test_is_valid_fresh_lock(self, valid_lock_context: LockContext) -> None:
        """Test that freshly created lock is valid."""
        assert valid_lock_context.is_valid() is True
        assert valid_lock_context.is_valid(ttl_seconds=3600) is True

    def test_matches_table_correct(self, valid_lock_context: LockContext) -> None:
        """Test matching correct table name."""
        assert valid_lock_context.matches_table("chembl_activity") is True

    def test_matches_table_exclusive(self, exclusive_lock_context: LockContext) -> None:
        """Test exclusive lock matches table."""
        assert exclusive_lock_context.matches_table("chembl_activity") is True

    def test_matches_table_wrong(self, valid_lock_context: LockContext) -> None:
        """Test matching wrong table name."""
        assert valid_lock_context.matches_table("pubchem_compound") is False
        assert valid_lock_context.matches_table("chembl_molecule") is False

    def test_immutability(self, valid_lock_context: LockContext) -> None:
        """Test that LockContext is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            valid_lock_context.key = "modified"  # type: ignore[misc]


class TestLockNotHeldError:
    """Tests for LockNotHeldError exception."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = LockNotHeldError("write_silver", "lock:chembl_activity")

        assert "write_silver" in str(error)
        assert "lock:chembl_activity" in str(error)
        assert error.operation == "write_silver"
        assert error.expected_key == "lock:chembl_activity"


class TestLockManagerGetContext:
    """Tests for LockManager.get_context() method."""

    @pytest.fixture
    def mock_lock_port(self) -> MagicMock:
        """Create mock LockPort with async methods."""
        from unittest.mock import AsyncMock

        mock = MagicMock()
        mock.acquire = AsyncMock(return_value=True)
        mock.release = AsyncMock(return_value=True)
        mock.heartbeat = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def mock_shutdown_signal(self) -> MagicMock:
        """Create mock ShutdownSignal."""
        mock = MagicMock()
        mock.is_requested = False
        return mock

    @pytest.mark.asyncio
    async def test_get_context_before_acquire(
        self,
        mock_lock_port: MagicMock,
        mock_shutdown_signal: MagicMock,
        mock_logger: MagicMock,
        run_id: RunID,
    ) -> None:
        """Test get_context returns None before lock is acquired."""
        from bioetl.application.core.lock_manager import LockManager

        manager = LockManager.create(
            lock_port=mock_lock_port,
            run_id=run_id,
            provider="chembl",
            entity_type="activity",
            run_type=RunType.INCREMENTAL,
            lock_ttl=3600,
            wait_for_lock=False,
            wait_timeout=300,
            heartbeat_interval=60,
            logger=mock_logger,
            shutdown_signal=mock_shutdown_signal,
        )

        ctx = manager.get_context()
        assert ctx is None

    @pytest.mark.asyncio
    async def test_get_context_after_acquire(
        self,
        mock_lock_port: MagicMock,
        mock_shutdown_signal: MagicMock,
        mock_logger: MagicMock,
        run_id: RunID,
    ) -> None:
        """Test get_context returns valid context after lock acquired."""
        from bioetl.application.core.lock_manager import LockManager

        manager = LockManager.create(
            lock_port=mock_lock_port,
            run_id=run_id,
            provider="chembl",
            entity_type="activity",
            run_type=RunType.INCREMENTAL,
            lock_ttl=3600,
            wait_for_lock=False,
            wait_timeout=300,
            heartbeat_interval=60,
            logger=mock_logger,
            shutdown_signal=mock_shutdown_signal,
        )

        await manager.acquire()
        ctx = manager.get_context()

        assert ctx is not None
        assert ctx.key == "lock:chembl_activity"
        assert ctx.owner_id == run_id
        assert ctx.exclusive is False
        assert ctx.is_valid() is True

    @pytest.mark.asyncio
    async def test_get_context_exclusive_lock(
        self,
        mock_lock_port: MagicMock,
        mock_shutdown_signal: MagicMock,
        mock_logger: MagicMock,
        run_id: RunID,
    ) -> None:
        """Test get_context for exclusive (backfill) lock."""
        from bioetl.application.core.lock_manager import LockManager

        manager = LockManager.create(
            lock_port=mock_lock_port,
            run_id=run_id,
            provider="chembl",
            entity_type="activity",
            run_type=RunType.BACKFILL,  # Triggers exclusive lock
            lock_ttl=3600,
            wait_for_lock=False,
            wait_timeout=300,
            heartbeat_interval=60,
            logger=mock_logger,
            shutdown_signal=mock_shutdown_signal,
        )

        await manager.acquire()
        ctx = manager.get_context()

        assert ctx is not None
        assert ctx.key == "lock:chembl_activity:exclusive"
        assert ctx.exclusive is True

    @pytest.mark.asyncio
    async def test_get_context_after_release(
        self,
        mock_lock_port: MagicMock,
        mock_shutdown_signal: MagicMock,
        mock_logger: MagicMock,
        run_id: RunID,
    ) -> None:
        """Test get_context returns None after lock released."""
        from bioetl.application.core.lock_manager import LockManager

        manager = LockManager.create(
            lock_port=mock_lock_port,
            run_id=run_id,
            provider="chembl",
            entity_type="activity",
            run_type=RunType.INCREMENTAL,
            lock_ttl=3600,
            wait_for_lock=False,
            wait_timeout=300,
            heartbeat_interval=60,
            logger=mock_logger,
            shutdown_signal=mock_shutdown_signal,
        )

        await manager.acquire()
        assert manager.get_context() is not None

        await manager.release()
        assert manager.get_context() is None
