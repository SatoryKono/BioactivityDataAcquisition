"""Architecture test: Lock Safety Guard.

Verifies that LockPort includes validate_owner method for Safety Guard.
This prevents split-brain scenarios where lock expires but writer continues.

REQ-ARCH-041: Lock validation before storage writes.
See CONSOLIDATED_REFACTORING_ANALYSIS.md P1.3 for rationale.
"""

from __future__ import annotations

import inspect

import pytest

from bioetl.domain.ports import LockPort
from bioetl.infrastructure.locking.memory_lock import MemoryLock


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

    def test_memory_lock_implements_validate_owner(self):
        """MemoryLock MUST implement validate_owner method."""
        lock = MemoryLock()

        assert hasattr(lock, "validate_owner"), (
            "MemoryLock MUST implement validate_owner() method from LockPort"
        )
        assert callable(lock.validate_owner)

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


class TestLockManagerSafetyGuard:
    """Tests for LockManager.validate() method."""

    def test_lock_manager_has_validate_method(self):
        """LockManager MUST expose validate() method for Safety Guard."""
        from bioetl.application.core.lock_manager import LockManager

        assert hasattr(LockManager, "validate"), (
            "LockManager MUST have validate() method for Safety Guard. "
            "This method wraps LockPort.validate_owner() for use in pipelines."
        )
