"""Coverage boost tests for silver_writer_maintenance_mixin.py.

Targets uncovered lines: 77-78, 212-219.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)


class _ConcreteMaintMixin(SilverWriterMaintenanceMixin):
    """Concrete subclass for testing."""

    def __init__(
        self,
        tmp_path: Path,
        csv_exporter: object | None = None,
    ) -> None:
        self.logger = MagicMock()
        self.csv_exporter = csv_exporter
        self._retention_manager = MagicMock()
        self.read_table = AsyncMock(return_value=[])
        self._tmp_path = tmp_path

    def get_table_path(self, name: str) -> Path:
        return self._tmp_path / name


@pytest.mark.unit
class TestMaybeExportCsvEdgeCases:
    """Tests for _maybe_export_csv (lines 77-78)."""

    @pytest.mark.asyncio
    async def test_csv_exporter_none_skips_export(self, tmp_path: Path) -> None:
        """Line 53-54: no csv_exporter set, export is skipped."""
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=None)
        data = pa.table({"id": [1, 2], "value": [10.0, 20.0]})

        # Should not raise — exporter is None
        await mixin._maybe_export_csv(
            table_name="chembl_activity",
            arrow_data=data,
            mode="merge",
            validated_mode=SilverWriteMode.MERGE,
            primary_keys=["id"],
        )

    @pytest.mark.asyncio
    async def test_csv_exporter_delete_mode_sets_append_false(
        self, tmp_path: Path
    ) -> None:
        """Line 55: delete mode → csv_append=False."""
        exporter = MagicMock()
        exporter.export = AsyncMock()
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=exporter)
        data = pa.table({"id": [1]})

        await mixin._maybe_export_csv(
            table_name="t",
            arrow_data=data,
            mode="delete",
            validated_mode=SilverWriteMode.DELETE,
            primary_keys=["id"],
        )

        call_kwargs = exporter.export.call_args[1]
        assert call_kwargs["append"] is False

    @pytest.mark.asyncio
    async def test_csv_exporter_merge_mode_passes_primary_keys(
        self, tmp_path: Path
    ) -> None:
        """Lines 56-63: merge mode passes primary_keys to exporter."""
        exporter = MagicMock()
        exporter.export = AsyncMock()
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=exporter)
        data = pa.table({"id": [1]})

        await mixin._maybe_export_csv(
            table_name="t",
            arrow_data=data,
            mode="merge",
            validated_mode=SilverWriteMode.MERGE,
            primary_keys=["id"],
        )

        call_kwargs = exporter.export.call_args[1]
        assert call_kwargs["primary_keys"] == ["id"]
        assert call_kwargs["append"] is True

    @pytest.mark.asyncio
    async def test_csv_exporter_append_mode_no_primary_keys(
        self, tmp_path: Path
    ) -> None:
        """Lines 56-57: append mode — csv_primary_keys is None."""
        exporter = MagicMock()
        exporter.export = AsyncMock()
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=exporter)
        data = pa.table({"id": [1]})

        await mixin._maybe_export_csv(
            table_name="t",
            arrow_data=data,
            mode="append",
            validated_mode=SilverWriteMode.APPEND,
            primary_keys=["id"],
        )

        call_kwargs = exporter.export.call_args[1]
        assert call_kwargs["primary_keys"] is None
        assert call_kwargs["append"] is True

    @pytest.mark.asyncio
    async def test_finalize_csv_with_exporter(self, tmp_path: Path) -> None:
        """Lines 77-78: finalize_csv_export calls csv_exporter.finalize_csv."""
        exporter = MagicMock()
        exporter.finalize_csv = AsyncMock()
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=exporter)

        await mixin.finalize_csv_export("t", primary_keys=["id"])

        exporter.finalize_csv.assert_called_once_with("t", primary_keys=["id"])

    @pytest.mark.asyncio
    async def test_finalize_csv_without_exporter_does_nothing(
        self, tmp_path: Path
    ) -> None:
        """Line 77: csv_exporter is None — finalize_csv_export does nothing."""
        mixin = _ConcreteMaintMixin(tmp_path, csv_exporter=None)

        # Should not raise
        await mixin.finalize_csv_export("t", primary_keys=["id"])


@pytest.mark.unit
class TestDelegationMethods:
    """Tests for delegation methods that forward to _retention_manager."""

    @pytest.mark.asyncio
    async def test_vacuum_delegates_to_retention_manager(self, tmp_path: Path) -> None:
        """vacuum delegates to _retention_manager.vacuum."""
        mixin = _ConcreteMaintMixin(tmp_path)
        mixin._retention_manager.vacuum = AsyncMock(return_value=["file1"])

        result = await mixin.vacuum("test_table", retention_hours=24, dry_run=True)

        mixin._retention_manager.vacuum.assert_called_once_with(
            "test_table", retention_hours=24, dry_run=True
        )
        assert result == ["file1"]

    @pytest.mark.asyncio
    async def test_optimize_delegates_to_retention_manager(
        self, tmp_path: Path
    ) -> None:
        """optimize delegates to _retention_manager.optimize."""
        mixin = _ConcreteMaintMixin(tmp_path)
        mixin._retention_manager.optimize = AsyncMock(return_value={"optimized": 5})

        result = await mixin.optimize("test_table")

        mixin._retention_manager.optimize.assert_called_once_with(
            "test_table", target_size=None, partition_filters=None
        )
        assert result == {"optimized": 5}

    @pytest.mark.asyncio
    async def test_deduplicate_silver_delegates__test_delegation_methods_infrastructure_storage_test_silver_writer_maintenance_boost_177(self, tmp_path: Path) -> None:
        """deduplicate_silver delegates to _retention_manager."""
        mixin = _ConcreteMaintMixin(tmp_path)
        mixin._retention_manager.deduplicate_silver = AsyncMock(return_value=5)

        result = await mixin.deduplicate_silver("test_table", primary_keys=["id"])

        assert result == 5

    @pytest.mark.asyncio
    async def test_read_silver_uses_read_table(self, tmp_path: Path) -> None:
        """read_silver calls self.read_table."""
        mixin = _ConcreteMaintMixin(tmp_path)
        mixin.read_table = AsyncMock(return_value=[{"id": 1}])

        result = await mixin.read_silver("test_table", columns=["id"])

        mixin.read_table.assert_called_once_with("test_table", columns=["id"])
        assert result == [{"id": 1}]
