"""Architecture test: Lock Safety Guard.

Verifies that LockPort includes fencing token validation for Safety Guard.
This prevents split-brain scenarios where lock expires but writer continues.

REQ-ARCH-041: Lock validation before storage writes.
See CONSOLIDATED_REFACTORING_ANALYSIS.md P1.3 for rationale.
"""

from __future__ import annotations

import inspect

import pytest

from bioetl.domain.locking import FencingToken
from bioetl.domain.ports import LockPort
from bioetl.infrastructure.locking.memory_lock import MemoryLock


pytestmark = pytest.mark.architecture

class TestLockSafetyGuard:
    """Tests for Lock Safety Guard implementation."""

    def test_lockport_has_validate_owner_method(self):
        """LockPort Protocol MUST define validate_owner method.

        This is the Safety Guard interface: before writing to storage,
        the writer SHOULD validate that it still holds the lock.
        """
        # Get all methods from LockPort protocol
        methods = [
            name
            for name, _ in inspect.getmembers(LockPort, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        assert "validate_owner" in methods, (
            "LockPort MUST define validate_owner() method for Safety Guard. "
            "This prevents split-brain scenarios where lock expires but writer continues."
        )

    def test_lockport_has_validate_fencing_token_method(self):
        """LockPort Protocol MUST define validate_fencing_token method."""
        methods = [
            name
            for name, _ in inspect.getmembers(LockPort, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        assert "validate_fencing_token" in methods, (
            "LockPort MUST define validate_fencing_token() for fencing validation."
        )

    def test_memory_lock_implements_validate_owner(self):
        """MemoryLock MUST implement validate_owner method."""
        lock = MemoryLock()

        assert hasattr(lock, "validate_owner"), (
            "MemoryLock MUST implement validate_owner() method from LockPort"
        )
        assert callable(lock.validate_owner)

    def test_memory_lock_implements_validate_fencing_token(self):
        """MemoryLock MUST implement validate_fencing_token method."""
        lock = MemoryLock()

        assert hasattr(lock, "validate_fencing_token"), (
            "MemoryLock MUST implement validate_fencing_token() method from LockPort"
        )
        assert callable(lock.validate_fencing_token)

    @pytest.mark.asyncio
    async def test_validate_owner_returns_true_when_holding_lock(self):
        """validate_owner returns True when run_id holds the lock."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id = uuid4()
        key = "test:lock"

        # Acquire lock
        acquired = await lock.acquire(key, run_id, ttl=60)
        assert acquired

        # Validate owner - should return True
        is_valid = await lock.validate_owner(key, run_id)
        assert is_valid is True

        await lock.release(key, run_id)
        await lock.aclose()

    @pytest.mark.asyncio
    async def test_validate_owner_returns_false_when_not_holding_lock(self):
        """validate_owner returns False when run_id does not hold the lock."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id_owner = uuid4()
        run_id_other = uuid4()
        key = "test:lock"

        # Acquire lock with owner
        acquired = await lock.acquire(key, run_id_owner, ttl=60)
        assert acquired

        # Validate with different run_id - should return False
        is_valid = await lock.validate_owner(key, run_id_other)
        assert is_valid is False

        await lock.release(key, run_id_owner)
        await lock.aclose()

    @pytest.mark.asyncio
    async def test_validate_owner_returns_false_for_nonexistent_lock(self):
        """validate_owner returns False for non-existent lock key."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id = uuid4()

        # Validate non-existent lock - should return False
        is_valid = await lock.validate_owner("nonexistent:key", run_id)
        assert is_valid is False

        await lock.aclose()

    @pytest.mark.asyncio
    async def test_validate_owner_returns_false_after_release(self):
        """validate_owner returns False after lock is released."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id = uuid4()
        key = "test:lock"

        # Acquire and release lock
        await lock.acquire(key, run_id, ttl=60)
        await lock.release(key, run_id)

        # Validate after release - should return False
        is_valid = await lock.validate_owner(key, run_id)
        assert is_valid is False

        await lock.aclose()

    @pytest.mark.asyncio
    async def test_validate_fencing_token_returns_true_when_holding_lock(self):
        """validate_fencing_token returns True when token matches holder."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id = uuid4()
        key = "test:lock"

        token = await lock.acquire(key, run_id, ttl=60)
        assert token is not None

        is_valid = await lock.validate_fencing_token(key, token)
        assert is_valid is True

        await lock.release(key, run_id)
        await lock.aclose()

    @pytest.mark.asyncio
    async def test_validate_fencing_token_rejects_stale_token(self):
        """validate_fencing_token returns False for stale tokens."""
        from uuid import uuid4

        lock = MemoryLock()
        key = "test:lock"

        run_id = uuid4()
        stale_token = await lock.acquire(key, run_id, ttl=60)
        assert stale_token is not None
        await lock.release(key, run_id)

        new_run = uuid4()
        new_token = await lock.acquire(key, new_run, ttl=60)
        assert new_token is not None

        is_valid = await lock.validate_fencing_token(key, stale_token)
        assert is_valid is False

        await lock.release(key, new_run)
        await lock.aclose()


class TestFencingTokenContract:
    """Tests for FencingToken fencing contract."""

    def test_lockport_acquire_returns_fencing_token(self):
        """LockPort.acquire() MUST return FencingToken | None, not bool."""
        import typing

        hints = typing.get_type_hints(LockPort.acquire)
        return_type = hints.get("return")
        # The return type should include FencingToken (via Union with None)
        assert return_type is not None, "acquire() must have a return type annotation"
        # Check it's not bool
        assert return_type is not bool, (
            "LockPort.acquire() must return FencingToken | None, not bool"
        )

    @pytest.mark.asyncio
    async def test_memory_lock_acquire_returns_fencing_token(self):
        """MemoryLock.acquire() MUST return FencingToken on success."""
        from uuid import uuid4

        lock = MemoryLock()
        run_id = uuid4()

        token = await lock.acquire("test:key", run_id, ttl=60)
        assert isinstance(token, FencingToken), (
            f"acquire() must return FencingToken, got {type(token)}"
        )
        assert token.sequence > 0
        assert token.key == "test:key"
        assert token.owner_id == run_id

        await lock.release("test:key", run_id)
        await lock.aclose()

    @pytest.mark.asyncio
    async def test_fencing_token_sequence_is_monotonic(self):
        """FencingToken sequence MUST increase across successive acquires."""
        from uuid import uuid4

        lock = MemoryLock()

        tokens = []
        for _ in range(3):
            run_id = uuid4()
            token = await lock.acquire("test:key", run_id, ttl=60)
            assert token is not None
            tokens.append(token)
            await lock.release("test:key", run_id)

        for i in range(1, len(tokens)):
            assert tokens[i].sequence > tokens[i - 1].sequence, (
                "FencingToken sequence must be monotonically increasing"
            )

        await lock.aclose()


class TestLockRuntimeServiceSafetyGuard:
    """Tests for LockRuntimeService.validate() method."""

    def test_lock_manager_has_validate_method(self):
        """LockRuntimeService MUST expose validate() method for Safety Guard."""
        from bioetl.application.core.lifecycle.lock_runtime_service import (
            LockRuntimeService,
        )

        assert hasattr(LockRuntimeService, "validate"), (
            "LockRuntimeService MUST have validate() method for Safety Guard. "
            "This method wraps fencing token validation for use in pipelines."
        )
