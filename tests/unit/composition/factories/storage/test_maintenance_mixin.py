"""Unit tests for StorageAdapterMaintenanceMixin."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.storage.maintenance_mixin import (
    StorageAdapterMaintenanceMixin,
    _is_delta_table_dir,
)


def _make_mixin(
    *,
    silver_get_table_path: Path | None = None,
    gold_get_table_path: Path | None = None,
) -> StorageAdapterMaintenanceMixin:
    """Create a MaintenanceMixin with stub writers."""
    mixin = StorageAdapterMaintenanceMixin.__new__(StorageAdapterMaintenanceMixin)
    mixin.bronze = SimpleNamespace(
        cleanup_old_files=AsyncMock(return_value={"removed": 3}),
    )  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(
        get_table_path=MagicMock(
            return_value=silver_get_table_path or Path("/nonexistent")
        ),
        vacuum=AsyncMock(return_value=["file1", "file2"]),
        deduplicate_silver=AsyncMock(return_value=5),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        get_table_path=MagicMock(
            return_value=gold_get_table_path or Path("/nonexistent")
        ),
    )  # type: ignore[assignment]
    return mixin


@pytest.mark.unit
def test_is_delta_table_dir_false_no_delta_log(tmp_path: Path) -> None:
    """_is_delta_table_dir returns False when _delta_log directory does not exist."""
    assert _is_delta_table_dir(tmp_path) is False


@pytest.mark.unit
def test_is_delta_table_dir_false_empty_delta_log(tmp_path: Path) -> None:
    """_is_delta_table_dir returns False when _delta_log is empty."""
    (tmp_path / "_delta_log").mkdir()
    assert _is_delta_table_dir(tmp_path) is False


@pytest.mark.unit
def test_is_delta_table_dir_true_with_commit(tmp_path: Path) -> None:
    """_is_delta_table_dir returns True when _delta_log has files."""
    delta_log = tmp_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "00000000000000000000.json").touch()
    assert _is_delta_table_dir(tmp_path) is True


@pytest.mark.unit
def test_is_table_initialized_silver(tmp_path: Path) -> None:
    """is_table_initialized checks silver layer by default."""
    delta_log = tmp_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "commit.json").touch()
    mixin = _make_mixin(silver_get_table_path=tmp_path)
    assert mixin.is_table_initialized("chembl.activity") is True


@pytest.mark.unit
def test_is_table_initialized_gold(tmp_path: Path) -> None:
    """is_table_initialized checks gold layer when specified."""
    delta_log = tmp_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "commit.json").touch()
    mixin = _make_mixin(gold_get_table_path=tmp_path)
    assert mixin.is_table_initialized("chembl.activity", layer="gold") is True


@pytest.mark.unit
def test_is_table_initialized_false(tmp_path: Path) -> None:
    """is_table_initialized returns False for non-delta directory."""
    mixin = _make_mixin(silver_get_table_path=tmp_path)
    assert mixin.is_table_initialized("chembl.activity") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vacuum_silver_only(tmp_path: Path) -> None:
    """vacuum processes silver when delta table exists, skips gold."""
    silver_path = tmp_path / "silver"
    silver_path.mkdir()
    delta_log = silver_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "commit.json").touch()

    mixin = _make_mixin(silver_get_table_path=silver_path)
    result = await mixin.vacuum("chembl.activity", retention_hours=72)
    assert result == 2  # len(["file1", "file2"])
    mixin.silver.vacuum.assert_called_once_with(
        table_name="chembl.activity",
        retention_hours=72,
        dry_run=False,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vacuum_no_tables() -> None:
    """vacuum returns 0 when no delta tables exist."""
    mixin = _make_mixin()
    result = await mixin.vacuum("chembl.activity")
    assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optimize_delegates_to_vacuum_and_bronze(tmp_path: Path) -> None:
    """optimize calls vacuum + bronze cleanup for dotted table names."""
    silver_path = tmp_path / "silver"
    silver_path.mkdir()
    delta_log = silver_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "commit.json").touch()

    mixin = _make_mixin(silver_get_table_path=silver_path)
    await mixin.optimize("chembl.activity", retention_hours=48, dry_run=True)
    mixin.bronze.cleanup_old_files.assert_called_once()
    call_kwargs = mixin.bronze.cleanup_old_files.call_args[1]
    assert call_kwargs["dry_run"] is True
    assert call_kwargs["provider"] == "chembl"
    assert call_kwargs["entity"] == "activity"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optimize_uses_sanctioned_time_for_cutoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """optimize should derive Bronze cutoff from the sanctioned time helper."""
    silver_path = tmp_path / "silver"
    silver_path.mkdir()
    delta_log = silver_path / "_delta_log"
    delta_log.mkdir()
    (delta_log / "commit.json").touch()

    fixed_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.composition.factories.storage.maintenance_mixin.current_utc_time",
        lambda: fixed_now,
    )

    mixin = _make_mixin(silver_get_table_path=silver_path)
    await mixin.optimize("chembl.activity", retention_hours=48, dry_run=True)

    call_kwargs = mixin.bronze.cleanup_old_files.call_args[1]
    assert call_kwargs["cutoff_date"] == datetime(2026, 4, 22, 12, 0, tzinfo=UTC)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optimize_no_dot_in_table_name(tmp_path: Path) -> None:
    """optimize skips bronze cleanup when table_name has no dot."""
    mixin = _make_mixin()
    await mixin.optimize("simple_table")
    mixin.bronze.cleanup_old_files.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_silver_and_gold(tmp_path: Path) -> None:
    """archive copies silver and gold table directories to target."""
    silver_source = tmp_path / "silver_src"
    silver_source.mkdir()
    (silver_source / "data.parquet").touch()

    gold_source = tmp_path / "gold_src"
    gold_source.mkdir()
    (gold_source / "data.parquet").touch()
    (gold_source / "meta.json").touch()

    target = tmp_path / "archive"

    mixin = StorageAdapterMaintenanceMixin.__new__(StorageAdapterMaintenanceMixin)
    mixin.bronze = SimpleNamespace()  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(
        get_table_path=MagicMock(return_value=silver_source),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        get_table_path=MagicMock(return_value=gold_source),
    )  # type: ignore[assignment]

    result = await mixin.archive("chembl.activity", str(target))
    assert result == 3  # 1 silver + 2 gold files


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_with_remove_source(tmp_path: Path) -> None:
    """archive removes source directories when remove_source=True."""
    silver_source = tmp_path / "silver_src"
    silver_source.mkdir()
    (silver_source / "data.parquet").touch()

    gold_source = tmp_path / "gold_src"
    gold_source.mkdir()
    (gold_source / "data.parquet").touch()

    target = tmp_path / "archive"

    mixin = StorageAdapterMaintenanceMixin.__new__(StorageAdapterMaintenanceMixin)
    mixin.bronze = SimpleNamespace()  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(
        get_table_path=MagicMock(return_value=silver_source),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        get_table_path=MagicMock(return_value=gold_source),
    )  # type: ignore[assignment]

    await mixin.archive("chembl.activity", str(target), remove_source=True)
    assert not silver_source.exists()
    assert not gold_source.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_nonexistent_returns_zero() -> None:
    """archive returns 0 when source paths don't exist."""
    mixin = StorageAdapterMaintenanceMixin.__new__(StorageAdapterMaintenanceMixin)
    mixin.bronze = SimpleNamespace()  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(
        get_table_path=MagicMock(return_value=Path("/nonexistent/silver")),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        get_table_path=MagicMock(return_value=Path("/nonexistent/gold")),
    )  # type: ignore[assignment]

    result = await mixin.archive("test.table", "test-output/archive")
    assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deduplicate_silver_delegates() -> None:
    """deduplicate_silver delegates to silver writer."""
    mixin = _make_mixin()
    result = await mixin.deduplicate_silver("chembl.activity", ["id"])
    assert result == 5
    mixin.silver.deduplicate_silver.assert_called_once_with("chembl.activity", ["id"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_bronze_delegates() -> None:
    """cleanup_bronze delegates to bronze writer."""
    mixin = _make_mixin()
    cutoff = datetime(2024, 1, 1, tzinfo=UTC)
    result = await mixin.cleanup_bronze(cutoff, dry_run=True)
    assert result == {"removed": 3}
    mixin.bronze.cleanup_old_files.assert_called_once_with(
        cutoff_date=cutoff,
        dry_run=True,
    )
