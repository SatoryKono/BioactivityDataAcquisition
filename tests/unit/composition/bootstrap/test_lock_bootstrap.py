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
"""Unit tests for bootstrap lock service function.

Tests bootstrap functions for lock service used by CLI operations.
"""

from __future__ import annotations

import pytest

from bioetl.application.services.lock_service import LockService
from bioetl.composition.bootstrap.cli.lock import bootstrap_lock_service
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestBootstrapLockService:
    """Tests for bootstrap_lock_service function."""

    def test_bootstrap_lock_service_returns_lock_service(self):
        """Test that bootstrap_lock_service returns a LockService instance."""
        result = bootstrap_lock_service()

        assert isinstance(result, LockService)

    def test_bootstrap_lock_service_wires_memory_lock(self):
        """Test that bootstrap_lock_service wires MemoryLock as the lock port."""
        result = bootstrap_lock_service()

        # LockService uses lock_port attribute (dataclass)
        assert isinstance(result.lock_port, MemoryLock)

    def test_bootstrap_lock_service_wires_noop_logger(self):
        """Test that bootstrap_lock_service wires NoOpLogger as the logger."""
        result = bootstrap_lock_service()

        # LockService uses logger attribute (dataclass)
        assert isinstance(result.logger, NoOpLogger)

    @pytest.mark.asyncio
    async def test_bootstrap_lock_service_can_list_locks(self):
        """Test that the bootstrapped LockService can list locks."""
        service = bootstrap_lock_service()

        # The service should be functional - using correct method name
        result = await service.list_locks()
        assert isinstance(result, list)
        assert len(result) == 0  # No locks initially

    @pytest.mark.asyncio
    async def test_bootstrap_lock_service_lock_operations(self):
        """Test that the bootstrapped LockService supports lock operations."""
        service = bootstrap_lock_service()

        # Acquire a lock via the underlying port
        lock_key = "test:lock"
        owner_id = "test_owner"
        acquired = await service.lock_port.acquire(
            key=lock_key,
            owner_id=owner_id,
            ttl=60.0,
        )
        assert acquired is not None

        # Validate the lock is held by the correct owner
        is_valid = await service.lock_port.validate_owner(
            key=lock_key, owner_id=owner_id
        )
        assert is_valid is True

        # Different owner should not be valid
        is_other_valid = await service.lock_port.validate_owner(
            key=lock_key, owner_id="other_owner"
        )
        assert is_other_valid is False

        # Release the lock
        released = await service.lock_port.release(key=lock_key, owner_id=owner_id)
        assert released is True

        # After release, validate_owner should return False
        is_still_valid = await service.lock_port.validate_owner(
            key=lock_key, owner_id=owner_id
        )
        assert is_still_valid is False
