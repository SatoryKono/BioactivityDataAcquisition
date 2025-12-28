"""Tests for writer lock validation (RULES.md §3.3).

Verifies that storage writers correctly validate lock context before
performing write operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.domain.locking import LockContext, LockNotHeldError
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.delta_writer import DeltaWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock(spec=["info", "error", "warning", "debug"])


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics port."""
    return MagicMock()


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


@pytest.fixture
def wrong_table_lock_context(run_id: RunID) -> LockContext:
    """Create a lock context for wrong table (pubchem_compound)."""
    return LockContext.create(
        provider="pubchem",
        entity="compound",
        owner_id=run_id,
        exclusive=False,
    )


@pytest.fixture
def different_owner_id() -> RunID:
    """Create a different run ID (simulates lock re-acquisition)."""
    return RunID(uuid4())


@pytest.fixture
def wrong_owner_lock_context(different_owner_id: RunID) -> LockContext:
    """Create a lock context with different owner (fencing token mismatch)."""
    return LockContext.create(
        provider="chembl",
        entity="activity",
        owner_id=different_owner_id,
        exclusive=False,
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


class TestDeltaWriterLockValidation:
    """Tests for DeltaWriter lock validation."""

    @pytest.fixture
    def delta_writer(self, tmp_path: Path, mock_logger: MagicMock) -> DeltaWriter:
        """Create DeltaWriter with require_lock=True."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        return DeltaWriter(
            base_path=tmp_path,
            logger=mock_logger,
            require_lock=True,
        )

    @pytest.fixture
    def delta_writer_no_lock(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> DeltaWriter:
        """Create DeltaWriter with require_lock=False."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        return DeltaWriter(
            base_path=tmp_path,
            logger=mock_logger,
            require_lock=False,
        )

    @pytest.fixture
    def sample_schema(self) -> pa.Schema:
        """Create sample PyArrow schema."""
        return pa.schema([
            pa.field("id", pa.int64()),
            pa.field("name", pa.string()),
        ])

    def test_validate_lock_held_no_context(
        self, delta_writer: DeltaWriter, mock_logger: MagicMock
    ) -> None:
        """Test validation fails when no lock context provided."""
        with pytest.raises(LockNotHeldError) as exc_info:
            delta_writer._validate_lock_held("chembl_activity", None)

        assert "lock:chembl_activity" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_wrong_table(
        self,
        delta_writer: DeltaWriter,
        wrong_table_lock_context: LockContext,
        mock_logger: MagicMock,
    ) -> None:
        """Test validation fails when lock is for wrong table."""
        with pytest.raises(LockNotHeldError) as exc_info:
            delta_writer._validate_lock_held("chembl_activity", wrong_table_lock_context)

        assert "lock:chembl_activity" in str(exc_info.value)
        assert "pubchem_compound" in str(exc_info.value)

    def test_validate_lock_held_valid(
        self,
        delta_writer: DeltaWriter,
        valid_lock_context: LockContext,
    ) -> None:
        """Test validation passes with valid lock context."""
        # Should not raise
        delta_writer._validate_lock_held("chembl_activity", valid_lock_context)

    def test_validate_lock_held_exclusive_accepted(
        self,
        delta_writer: DeltaWriter,
        exclusive_lock_context: LockContext,
    ) -> None:
        """Test exclusive lock is accepted for normal writes."""
        # Should not raise
        delta_writer._validate_lock_held("chembl_activity", exclusive_lock_context)

    def test_validate_lock_disabled(
        self,
        delta_writer_no_lock: DeltaWriter,
    ) -> None:
        """Test validation is skipped when require_lock=False."""
        # Should not raise even with None
        delta_writer_no_lock._validate_lock_held("chembl_activity", None)

    def test_validate_lock_held_wrong_owner_id(
        self,
        delta_writer: DeltaWriter,
        wrong_owner_lock_context: LockContext,
        run_id: RunID,
        mock_logger: MagicMock,
    ) -> None:
        """Test validation fails when lock has wrong owner_id (fencing token mismatch)."""
        with pytest.raises(LockNotHeldError) as exc_info:
            delta_writer._validate_lock_held(
                "chembl_activity",
                wrong_owner_lock_context,
                expected_owner_id=run_id,  # Different from wrong_owner_lock_context.owner_id
            )

        assert "owner mismatch" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_matching_owner_id(
        self,
        delta_writer: DeltaWriter,
        valid_lock_context: LockContext,
        run_id: RunID,
    ) -> None:
        """Test validation passes when owner_id matches expected."""
        # Should not raise - owner_id matches
        delta_writer._validate_lock_held(
            "chembl_activity",
            valid_lock_context,
            expected_owner_id=run_id,
        )

    def test_validate_lock_held_no_expected_owner_skips_check(
        self,
        delta_writer: DeltaWriter,
        valid_lock_context: LockContext,
    ) -> None:
        """Test validation passes when expected_owner_id is None (backward compat)."""
        # Should not raise - no owner check when expected_owner_id is None
        delta_writer._validate_lock_held(
            "chembl_activity",
            valid_lock_context,
            expected_owner_id=None,
        )


class TestGoldWriterLockValidation:
    """Tests for GoldWriter lock validation."""

    @pytest.fixture
    def gold_writer(self, tmp_path: Path, mock_logger: MagicMock) -> GoldWriter:
        """Create GoldWriter with require_lock=True."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriter

        return GoldWriter(
            base_path=tmp_path,
            logger=mock_logger,
            require_lock=True,
        )

    @pytest.fixture
    def gold_writer_no_lock(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> GoldWriter:
        """Create GoldWriter with require_lock=False."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriter

        return GoldWriter(
            base_path=tmp_path,
            logger=mock_logger,
            require_lock=False,
        )

    def test_validate_lock_held_no_context(
        self, gold_writer: GoldWriter, mock_logger: MagicMock
    ) -> None:
        """Test validation fails when no lock context provided."""
        with pytest.raises(LockNotHeldError) as exc_info:
            gold_writer._validate_lock_held("chembl_activity", None)

        assert "write_gold" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_valid(
        self,
        gold_writer: GoldWriter,
        valid_lock_context: LockContext,
    ) -> None:
        """Test validation passes with valid lock context."""
        # Should not raise
        gold_writer._validate_lock_held("chembl_activity", valid_lock_context)

    def test_validate_lock_disabled(
        self,
        gold_writer_no_lock: GoldWriter,
    ) -> None:
        """Test validation is skipped when require_lock=False."""
        # Should not raise even with None
        gold_writer_no_lock._validate_lock_held("chembl_activity", None)

    def test_validate_lock_held_wrong_owner_id(
        self,
        gold_writer: GoldWriter,
        wrong_owner_lock_context: LockContext,
        run_id: RunID,
        mock_logger: MagicMock,
    ) -> None:
        """Test validation fails when lock has wrong owner_id (fencing token mismatch)."""
        with pytest.raises(LockNotHeldError) as exc_info:
            gold_writer._validate_lock_held(
                "chembl_activity",
                wrong_owner_lock_context,
                expected_owner_id=run_id,
            )

        assert "owner mismatch" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_matching_owner_id(
        self,
        gold_writer: GoldWriter,
        valid_lock_context: LockContext,
        run_id: RunID,
    ) -> None:
        """Test validation passes when owner_id matches expected."""
        # Should not raise
        gold_writer._validate_lock_held(
            "chembl_activity",
            valid_lock_context,
            expected_owner_id=run_id,
        )


class TestBronzeWriterLockValidation:
    """Tests for BronzeWriter lock validation."""

    @pytest.fixture
    def bronze_writer(
        self, tmp_path: Path, mock_logger: MagicMock, mock_metrics: MagicMock
    ) -> BronzeWriter:
        """Create BronzeWriter with require_lock=True."""
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

        return BronzeWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metrics=mock_metrics,
            require_lock=True,
        )

    @pytest.fixture
    def bronze_writer_no_lock(
        self, tmp_path: Path, mock_logger: MagicMock, mock_metrics: MagicMock
    ) -> BronzeWriter:
        """Create BronzeWriter with require_lock=False."""
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

        return BronzeWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metrics=mock_metrics,
            require_lock=False,
        )

    def test_validate_lock_held_no_context(
        self, bronze_writer: BronzeWriter, mock_logger: MagicMock
    ) -> None:
        """Test validation fails when no lock context provided."""
        with pytest.raises(LockNotHeldError) as exc_info:
            bronze_writer._validate_lock_held("chembl", "activity", None)

        assert "write_bronze" in str(exc_info.value)
        assert "lock:chembl_activity" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_wrong_provider(
        self,
        bronze_writer: BronzeWriter,
        wrong_table_lock_context: LockContext,
        mock_logger: MagicMock,
    ) -> None:
        """Test validation fails when lock is for wrong provider/entity."""
        with pytest.raises(LockNotHeldError) as exc_info:
            bronze_writer._validate_lock_held(
                "chembl", "activity", wrong_table_lock_context
            )

        assert "lock:chembl_activity" in str(exc_info.value)

    def test_validate_lock_held_valid(
        self,
        bronze_writer: BronzeWriter,
        valid_lock_context: LockContext,
    ) -> None:
        """Test validation passes with valid lock context."""
        # Should not raise
        bronze_writer._validate_lock_held("chembl", "activity", valid_lock_context)

    def test_validate_lock_disabled(
        self,
        bronze_writer_no_lock: BronzeWriter,
    ) -> None:
        """Test validation is skipped when require_lock=False."""
        # Should not raise even with None
        bronze_writer_no_lock._validate_lock_held("chembl", "activity", None)

    def test_validate_lock_held_wrong_owner_id(
        self,
        bronze_writer: BronzeWriter,
        wrong_owner_lock_context: LockContext,
        run_id: RunID,
        mock_logger: MagicMock,
    ) -> None:
        """Test validation fails when lock has wrong owner_id (fencing token mismatch)."""
        with pytest.raises(LockNotHeldError) as exc_info:
            bronze_writer._validate_lock_held(
                "chembl",
                "activity",
                wrong_owner_lock_context,
                expected_owner_id=run_id,
            )

        assert "owner mismatch" in str(exc_info.value)
        mock_logger.error.assert_called()

    def test_validate_lock_held_matching_owner_id(
        self,
        bronze_writer: BronzeWriter,
        valid_lock_context: LockContext,
        run_id: RunID,
    ) -> None:
        """Test validation passes when owner_id matches expected."""
        # Should not raise
        bronze_writer._validate_lock_held(
            "chembl",
            "activity",
            valid_lock_context,
            expected_owner_id=run_id,
        )


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
