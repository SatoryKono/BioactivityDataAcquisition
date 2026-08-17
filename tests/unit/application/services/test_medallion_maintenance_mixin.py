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
"""Direct unit tests for the medallion maintenance mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.medallion.medallion_maintenance_mixin import (
    _MedallionMaintenanceMixin,
)


class _MaintenanceHarness(_MedallionMaintenanceMixin):
    def __init__(self, storage: object, logger: object) -> None:
        self.storage = storage
        self.logger = logger


@pytest.mark.unit
class TestMedallionMaintenanceMixin:
    @pytest.mark.asyncio
    async def test_vacuum_delegates_to_storage_and_logs(self) -> None:
        storage = MagicMock()
        storage.vacuum = AsyncMock(return_value=7)
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        result = await service.vacuum("silver.activity", retention_days=3, dry_run=True)

        assert result == 7
        storage.vacuum.assert_awaited_once_with(
            table_name="silver.activity",
            retention_hours=72,
            dry_run=True,
        )
        assert logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_vacuum_logs_and_reraises_errors(self) -> None:
        storage = MagicMock()
        storage.vacuum = AsyncMock(side_effect=RuntimeError("boom"))
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        with pytest.raises(RuntimeError, match="boom"):
            await service.vacuum("silver.activity")

        logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_vacuum_rejects_negative_retention_days(self) -> None:
        storage = MagicMock()
        storage.vacuum = AsyncMock(return_value=0)
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        with pytest.raises(ValueError, match="retention_days must be >= 0"):
            await service.vacuum("silver.activity", retention_days=-1)

        storage.vacuum.assert_not_called()

    @pytest.mark.asyncio
    async def test_vacuum_allows_zero_retention_days(self) -> None:
        storage = MagicMock()
        storage.vacuum = AsyncMock(return_value=1)
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        result = await service.vacuum("silver.activity", retention_days=0)

        assert result == 1
        storage.vacuum.assert_awaited_once_with(
            table_name="silver.activity",
            retention_hours=0,
            dry_run=False,
        )

    @pytest.mark.asyncio
    async def test_archive_delegates_to_storage_and_logs(self) -> None:
        storage = MagicMock()
        storage.archive = AsyncMock(return_value=12)
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        result = await service.archive(
            "gold.activity",
            "/archive/gold/activity",
            remove_source=True,
        )

        assert result == 12
        storage.archive.assert_awaited_once_with(
            table_name="gold.activity",
            target_path="/archive/gold/activity",
            remove_source=True,
        )
        assert logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_archive_logs_and_reraises_errors(self) -> None:
        storage = MagicMock()
        storage.archive = AsyncMock(side_effect=ValueError("archive failed"))
        logger = MagicMock()
        service = _MaintenanceHarness(storage=storage, logger=logger)

        with pytest.raises(ValueError, match="archive failed"):
            await service.archive("gold.activity", "/archive/path")

        logger.error.assert_called_once()
