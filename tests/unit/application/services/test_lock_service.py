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
"""Unit tests for LockService.

Tests the lock administrative service.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.services.lock_service import (
    LockInfo,
    LockService,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_lock_port():
    """Create a mock lock port."""
    port = MagicMock()
    port.validate_owner = AsyncMock(return_value=False)
    port.release = AsyncMock(return_value=False)
    port.aclose = AsyncMock()
    return port


@pytest.fixture
def lock_service(mock_lock_port, mock_logger):
    """Create a LockService instance."""
    return LockService(
        lock_port=mock_lock_port,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestLockInfo:
    """Test LockInfo dataclass."""

    def test_lock_info_creation(self):
        """Test LockInfo can be created."""
        info = LockInfo(
            key="pipeline1",
            owner_id="run-123",
            exclusive=True,
        )

        assert info.key == "pipeline1"
        assert info.owner_id == "run-123"
        assert info.exclusive is True


@pytest.mark.unit
class TestLockServiceCheckLock:
    """Test LockService.check_lock method."""

    @pytest.mark.asyncio
    async def test_check_lock_not_held(self, lock_service, mock_lock_port):
        """Test checking a lock that is not held."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.validate_owner.return_value = False

        result = await lock_service.check_lock("pipeline1", owner_id)

        assert result is False
        mock_lock_port.validate_owner.assert_called_once_with(
            key="pipeline1",
            owner_id=owner_id,
        )

    @pytest.mark.asyncio
    async def test_check_lock_held(self, lock_service, mock_lock_port):
        """Test checking a lock that is held."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.validate_owner.return_value = True

        result = await lock_service.check_lock("pipeline1", owner_id)

        assert result is True


@pytest.mark.unit
class TestLockServiceReleaseLock:
    """Test LockService.release_lock method."""

    @pytest.mark.asyncio
    async def test_release_lock_not_held(self, lock_service, mock_lock_port):
        """Test releasing a lock that is not held."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.release.return_value = False

        result = await lock_service.release_lock("pipeline1", owner_id)

        assert result is False
        mock_lock_port.release.assert_called_once_with(
            key="pipeline1",
            owner_id=owner_id,
            exclusive=False,
        )

    @pytest.mark.asyncio
    async def test_service_release_lock__release_lock_success__f2bc3fe3(
        self, lock_service, mock_lock_port
    ):
        """Test successfully releasing a lock."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.release.return_value = True

        result = await lock_service.release_lock("pipeline1", owner_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_release_exclusive_lock(self, lock_service, mock_lock_port):
        """Test releasing an exclusive lock."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.release.return_value = True

        result = await lock_service.release_lock("pipeline1", owner_id, exclusive=True)

        assert result is True
        mock_lock_port.release.assert_called_once_with(
            key="pipeline1",
            owner_id=owner_id,
            exclusive=True,
        )


@pytest.mark.unit
class TestLockServiceForceReleaseAll:
    """Test LockService.force_release_all method."""

    @pytest.mark.asyncio
    async def test_force_release_all_none_held(self, lock_service, mock_lock_port):
        """Test force releasing when no locks are held."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        mock_lock_port.release.return_value = False

        result = await lock_service.force_release_all(
            owner_id, ["pipeline1", "pipeline2"]
        )

        assert result == []
        assert mock_lock_port.release.call_count == 4  # 2 regular + 2 exclusive

    @pytest.mark.asyncio
    async def test_force_release_all_some_held(self, lock_service, mock_lock_port):
        """Test force releasing when some locks are held."""
        owner_id = deterministic_run_uuid_from_callsite("test_lock_service")
        # First call (regular) succeeds for pipeline1 → exclusive not called
        # Second call (regular) fails for pipeline2 → try exclusive
        # Third call (exclusive) succeeds for pipeline2
        mock_lock_port.release.side_effect = [True, False, True]

        result = await lock_service.force_release_all(
            owner_id, ["pipeline1", "pipeline2"]
        )

        assert "pipeline1" in result
        assert "pipeline2:exclusive" in result


@pytest.mark.unit
class TestLockServiceListLocks:
    """Test LockService.list_locks method."""

    @pytest.mark.asyncio
    async def test_list_locks_not_supported(self, lock_service, mock_logger):
        """Test listing locks returns empty (not supported by LockPort)."""
        result = await lock_service.list_locks()

        assert result == []
        # Should log a warning
        mock_logger.warning.assert_called()


@pytest.mark.unit
class TestLockServiceAclose:
    """Test LockService.aclose method."""

    @pytest.mark.asyncio
    async def test_lock_service_aclose__aclose__7008566b(
        self, lock_service, mock_lock_port
    ):
        """Test closing the service."""
        await lock_service.aclose()

        mock_lock_port.aclose.assert_called_once()
