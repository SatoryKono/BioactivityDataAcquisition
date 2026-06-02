"""Tests for domain locking primitives (RULES.md §3.3).

Verifies LockContext value object and LockNotHeldError exception.

Note:
    Lock validation during writes is now performed at Application layer
    (BatchWriter) per RULES.md §4.6 Safety Guard. See test_batch_writer.py
    for those tests.
    Application orchestration checks for LockRuntimeService are covered in
    tests/unit/application/core/test_lock_manager_get_context.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.locking import FencingToken, LockContext, LockNotHeldError
from bioetl.domain.types import RunID


pytestmark = pytest.mark.unit


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


class TestFencingToken:
    """Tests for FencingToken value object."""

    def test_create_token(self, run_id: RunID) -> None:
        """Test creating a fencing token."""
        token = FencingToken(
            sequence=1,
            key="lock:chembl_activity",
            owner_id=run_id,
            issued_at=100.0,
        )

        assert token.sequence == 1
        assert token.key == "lock:chembl_activity"
        assert token.owner_id == run_id
        assert token.issued_at == pytest.approx(100.0)

    def test_locking_fencing_token__immutability__937636e8(self, run_id: RunID) -> None:
        """Test that FencingToken is immutable (frozen dataclass)."""
        token = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )

        with pytest.raises(AttributeError):
            token.sequence = 2  # type: ignore[misc]

    def test_value_equality(self, run_id: RunID) -> None:
        """Test that FencingTokens are compared by value."""
        t1 = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )
        t2 = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )

        assert t1 == t2

    def test_different_sequences_not_equal(self, run_id: RunID) -> None:
        """Test that tokens with different sequences are not equal."""
        t1 = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )
        t2 = FencingToken(
            sequence=2,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )

        assert t1 != t2

    def test_truthy(self, run_id: RunID) -> None:
        """Test that FencingToken is truthy (for backward-compatible checks)."""
        token = FencingToken(
            sequence=1,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )
        assert token  # truthy


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

    def test_fencing_token_field_default(self, valid_lock_context: LockContext) -> None:
        """Test that fencing_token defaults to None."""
        assert valid_lock_context.fencing_token is None

    def test_fencing_token_field_set(self, run_id: RunID) -> None:
        """Test LockContext with fencing token."""
        token = FencingToken(
            sequence=5,
            key="lock:test",
            owner_id=run_id,
            issued_at=100.0,
        )
        ctx = LockContext(key="lock:test", owner_id=run_id, fencing_token=token)

        assert ctx.fencing_token is not None
        assert ctx.fencing_token.sequence == 5

    def test_locking_lock_context__immutability__038767c5(
        self, valid_lock_context: LockContext
    ) -> None:
        """Test that LockContext is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            valid_lock_context.key = "modified"  # type: ignore[misc]


class TestLockNotHeldError:
    """Tests for LockNotHeldError exception."""

    def test_lock_not_held_error__error_message__57fd8f31(self) -> None:
        """Test error message format."""
        error = LockNotHeldError("write_silver", "lock:chembl_activity")

        assert "write_silver" in str(error)
        assert "lock:chembl_activity" in str(error)
        assert error.operation == "write_silver"
        assert error.expected_key == "lock:chembl_activity"
