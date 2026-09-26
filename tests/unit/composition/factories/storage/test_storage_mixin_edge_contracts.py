"""Edge-contract tests for storage bundle maintenance and write delegation."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.storage.maintenance_mixin import (
    StorageBundleMaintenanceMixin,
)
from bioetl.composition.factories.storage.write_mixin import StorageBundleWriteMixin
from bioetl.domain.ports.storage.silver_port import SilverWriteRequest
from bioetl.domain.types import ArrowSchema

pytestmark = pytest.mark.unit


def _delta_table_path(base_path: Path) -> Path:
    """Create the smallest valid on-disk Delta-table marker."""
    delta_log = base_path / "_delta_log"
    delta_log.mkdir(parents=True)
    (delta_log / "00000000000000000000.json").write_text("{}", encoding="utf-8")
    return base_path


def _maintenance_mixin(*, gold_path: Path) -> StorageBundleMaintenanceMixin:
    mixin = StorageBundleMaintenanceMixin.__new__(StorageBundleMaintenanceMixin)
    mixin.silver = cast(
        Any,
        SimpleNamespace(
            get_table_path=MagicMock(return_value=gold_path / "missing-silver"),
            vacuum=AsyncMock(return_value=[]),
        ),
    )
    mixin.gold = cast(
        Any,
        SimpleNamespace(get_table_path=MagicMock(return_value=gold_path)),
    )
    return mixin


def test_get_table_version_reads_initialized_delta_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An initialized table exposes the integer version from DeltaTable."""
    table_path = _delta_table_path(tmp_path / "silver")
    delta_table = MagicMock()
    delta_table.version.return_value = 17
    constructor = MagicMock(return_value=delta_table)
    monkeypatch.setattr("deltalake.DeltaTable", constructor)

    mixin = _maintenance_mixin(gold_path=tmp_path / "missing-gold")

    assert mixin.get_table_version(str(table_path)) == 17
    constructor.assert_called_once_with(str(table_path))


@pytest.mark.asyncio
async def test_vacuum_counts_gold_delta_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gold vacuum contributes its removed-file count when a Delta log exists."""
    gold_path = _delta_table_path(tmp_path / "gold")
    delta_table = MagicMock()
    delta_table.vacuum.return_value = ["old-1.parquet", "old-2.parquet"]
    constructor = MagicMock(return_value=delta_table)
    monkeypatch.setattr("deltalake.DeltaTable", constructor)
    mixin = _maintenance_mixin(gold_path=gold_path)

    removed = await mixin.vacuum(
        "chembl.activity",
        retention_hours=24,
        dry_run=True,
    )

    assert removed == 2
    constructor.assert_called_once_with(str(gold_path))
    delta_table.vacuum.assert_called_once_with(retention_hours=24, dry_run=True)


@pytest.mark.asyncio
async def test_vacuum_treats_gold_runtime_failure_as_no_removed_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recoverable Gold Delta failure must not invent a removal count."""
    gold_path = _delta_table_path(tmp_path / "gold")
    monkeypatch.setattr(
        "deltalake.DeltaTable",
        MagicMock(side_effect=RuntimeError("table is temporarily unavailable")),
    )
    mixin = _maintenance_mixin(gold_path=gold_path)

    assert await mixin.vacuum("chembl.activity") == 0


@pytest.mark.asyncio
async def test_write_silver_preserves_typed_request_boundary() -> None:
    """A canonical request object is passed through without legacy expansion."""
    silver = SimpleNamespace(write_silver=AsyncMock(return_value=object()))
    mixin = StorageBundleWriteMixin.__new__(StorageBundleWriteMixin)
    mixin.silver = cast(Any, silver)
    request = SilverWriteRequest(
        table_name="chembl.activity",
        records=[],
        primary_keys=["activity_id"],
        schema=cast(ArrowSchema, object()),
    )

    result = await mixin.write_silver(request)

    assert result is not None
    silver.write_silver.assert_awaited_once_with(request)
