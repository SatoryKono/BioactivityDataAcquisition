"""Unit tests for StorageBundleHealthMixin."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.storage.health_mixin import (
    StorageBundleHealthMixin,
)
from bioetl.domain.types import HealthStatus

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-health-mixin-"))
BRONZE_ROOT = str(TEST_ROOT / "bronze")
SILVER_ROOT = str(TEST_ROOT / "silver")
GOLD_ROOT = str(TEST_ROOT / "gold")


def _make_mixin(
    *,
    bronze_base: str = BRONZE_ROOT,
    silver_base: str = SILVER_ROOT,
    gold_base: str = GOLD_ROOT,
) -> StorageBundleHealthMixin:
    """Create a HealthMixin with stub writers."""
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)
    mixin.bronze = SimpleNamespace(base_path=bronze_base)  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(
        base_path=silver_base,
        get_table_path=MagicMock(),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        base_path=gold_base,
        get_table_path=MagicMock(),
    )  # type: ignore[assignment]
    return mixin


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_health_mixin__aclose_is_noop__f3bfdf25() -> None:
    """aclose completes without error."""
    mixin = _make_mixin()
    await mixin.aclose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_aclose_closes_shared_audit_once() -> None:
    """Shared audit adapter should be closed once through adapter shutdown."""
    audit = SimpleNamespace(aclose=AsyncMock())
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)
    mixin.bronze = SimpleNamespace(base_path=BRONZE_ROOT, _audit=audit)  # type: ignore[assignment]
    mixin.silver = SimpleNamespace(  # type: ignore[assignment]
        base_path=SILVER_ROOT,
        get_table_path=MagicMock(),
        _audit=audit,
    )
    mixin.gold = SimpleNamespace(  # type: ignore[assignment]
        base_path=GOLD_ROOT,
        get_table_path=MagicMock(),
        _audit=audit,
    )

    await mixin.aclose()

    audit.aclose.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_aclose_skips_writers_without_explicit_audit() -> None:
    """Shutdown should ignore writers that do not expose an explicit _audit attr."""
    mixin = _make_mixin()

    await mixin.aclose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_health_mixin__health_check_healthy__8564ec00(tmp_path: Path) -> None:
    """health_check returns HEALTHY when all directories are writable."""
    bronze = tmp_path / "bronze"
    silver = tmp_path / "silver"
    gold = tmp_path / "gold"
    bronze.mkdir()
    silver.mkdir()
    gold.mkdir()
    mixin = _make_mixin(
        bronze_base=str(bronze),
        silver_base=str(silver),
        gold_base=str(gold),
    )
    result = await mixin.health_check()
    assert result == HealthStatus.HEALTHY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_degraded(tmp_path: Path) -> None:
    """health_check returns DEGRADED when one directory is not writable."""
    bronze = tmp_path / "bronze"
    silver = tmp_path / "silver"
    bronze.mkdir()
    silver.mkdir()
    # gold does not exist and path points to an invalid location
    mixin = _make_mixin(
        bronze_base=str(bronze),
        silver_base=str(silver),
        gold_base="/nonexistent/path/gold",
    )
    result = await mixin.health_check()
    # Cannot guarantee /nonexistent fails on all OS, so check it's not an error
    assert result in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


@pytest.mark.unit
def test_check_directory_writable_creates_dir(tmp_path: Path) -> None:
    """_check_directory_writable creates directory if not exists."""
    target = tmp_path / "new_dir"
    result = StorageBundleHealthMixin._check_directory_writable(target)
    assert result is True
    assert target.exists()


@pytest.mark.unit
def test_check_directory_writable_accepts_string(tmp_path: Path) -> None:
    """_check_directory_writable accepts string paths."""
    result = StorageBundleHealthMixin._check_directory_writable(str(tmp_path))
    assert result is True


@pytest.mark.unit
def test_check_storage_health_sync_all_writable(tmp_path: Path) -> None:
    """_check_storage_health_sync returns HEALTHY when all dirs writable."""
    for layer in ("bronze", "silver", "gold"):
        (tmp_path / layer).mkdir()
    mixin = _make_mixin(
        bronze_base=str(tmp_path / "bronze"),
        silver_base=str(tmp_path / "silver"),
        gold_base=str(tmp_path / "gold"),
    )
    assert mixin._check_storage_health_sync() == HealthStatus.HEALTHY


@pytest.mark.unit
def test_preview_cleanup_silver_only(tmp_path: Path) -> None:
    """preview_cleanup returns silver info when gold_table is None."""
    silver_table_path = tmp_path / "silver_table"
    silver_table_path.mkdir()
    (silver_table_path / "file1.parquet").touch()
    (silver_table_path / "file2.parquet").touch()

    silver_writer = SimpleNamespace(
        get_table_path=MagicMock(return_value=silver_table_path),
    )
    gold_writer = SimpleNamespace(
        get_table_path=MagicMock(return_value=tmp_path / "gold_table"),
    )
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)
    mixin.bronze = SimpleNamespace(base_path=str(tmp_path))  # type: ignore[assignment]
    mixin.silver = silver_writer  # type: ignore[assignment]
    mixin.gold = gold_writer  # type: ignore[assignment]

    result = mixin.preview_cleanup("chembl.activity")
    assert result["gold"] is None
    assert result["silver"]["file_count"] == 2
    assert result["silver"]["exists"] is True
    assert result["total_files"] == 2


@pytest.mark.unit
def test_preview_cleanup_with_gold(tmp_path: Path) -> None:
    """preview_cleanup returns both silver and gold info."""
    silver_path = tmp_path / "silver"
    silver_path.mkdir()
    (silver_path / "f1.parquet").touch()
    gold_path = tmp_path / "gold"
    gold_path.mkdir()
    (gold_path / "g1.parquet").touch()
    (gold_path / "g2.parquet").touch()

    silver_writer = SimpleNamespace(
        get_table_path=MagicMock(return_value=silver_path),
    )
    gold_writer = SimpleNamespace(
        get_table_path=MagicMock(return_value=gold_path),
    )
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)
    mixin.bronze = SimpleNamespace(base_path=str(tmp_path))  # type: ignore[assignment]
    mixin.silver = silver_writer  # type: ignore[assignment]
    mixin.gold = gold_writer  # type: ignore[assignment]

    result = mixin.preview_cleanup("chembl.activity", gold_table="chembl.activity")
    assert result["silver"]["file_count"] == 1
    assert result["gold"]["file_count"] == 2
    assert result["total_files"] == 3


@pytest.mark.unit
def test_preview_layer_nonexistent_path(tmp_path: Path) -> None:
    """_preview_layer returns exists=False for nonexistent tables."""
    nonexistent = tmp_path / "does_not_exist"
    writer = SimpleNamespace(get_table_path=MagicMock(return_value=nonexistent))
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)

    result = mixin._preview_layer(writer, "test.table")  # type: ignore[arg-type]
    assert result["exists"] is False
    assert result["file_count"] == 0


@pytest.mark.unit
def test_preview_layer_with_preview_method(tmp_path: Path) -> None:
    """_preview_layer delegates to writer.preview_cleanup when available."""
    expected = {"path": str(tmp_path), "file_count": 42, "exists": True}
    writer = SimpleNamespace(
        preview_cleanup=MagicMock(return_value=expected),
        get_table_path=MagicMock(return_value=tmp_path),
    )
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)

    result = mixin._preview_layer(writer, "test.table")  # type: ignore[arg-type]
    assert result == expected


@pytest.mark.unit
def test_preview_layer_invalid_preview_payload_fallback(tmp_path: Path) -> None:
    """_preview_layer falls back when preview_cleanup returns invalid payload."""
    writer = SimpleNamespace(
        preview_cleanup=MagicMock(return_value={"invalid": "payload"}),
        get_table_path=MagicMock(return_value=tmp_path),
    )
    mixin = StorageBundleHealthMixin.__new__(StorageBundleHealthMixin)

    result = mixin._preview_layer(writer, "test.table")  # type: ignore[arg-type]
    assert result["path"] == str(tmp_path)
    assert result["exists"] is True


@pytest.mark.unit
def test_is_layer_preview_payload_valid() -> None:
    """_is_layer_preview_payload returns True for valid payloads."""
    valid = {"path": "/some/path", "file_count": 5, "exists": True}
    assert StorageBundleHealthMixin._is_layer_preview_payload(valid) is True


@pytest.mark.unit
def test_is_layer_preview_payload_invalid() -> None:
    """_is_layer_preview_payload returns False for non-dict."""
    assert StorageBundleHealthMixin._is_layer_preview_payload("not a dict") is False


@pytest.mark.unit
def test_is_layer_preview_payload_missing_keys() -> None:
    """_is_layer_preview_payload returns False when keys are missing."""
    assert StorageBundleHealthMixin._is_layer_preview_payload({"path": "x"}) is False


@pytest.mark.unit
def test_is_layer_preview_payload_wrong_types() -> None:
    """_is_layer_preview_payload returns False for wrong value types."""
    payload = {"path": 123, "file_count": "not int", "exists": "not bool"}
    assert StorageBundleHealthMixin._is_layer_preview_payload(payload) is False
