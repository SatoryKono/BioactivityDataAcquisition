"""Direct unit tests for the medallion maintenance mixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.medallion_maintenance_mixin import (
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
