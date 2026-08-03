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
"""Unit tests for StorageBundleMergedMixin."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.storage.merged_mixin import (
    StorageBundleMergedMixin,
)


def _make_mixin() -> StorageBundleMergedMixin:
    """Create a MergedMixin with stub writers."""
    mixin = StorageBundleMergedMixin.__new__(StorageBundleMergedMixin)
    mixin.silver = SimpleNamespace(
        get_table_path=MagicMock(return_value=Path("/silver/table")),
        read_silver=AsyncMock(return_value=[{"id": 1}]),
        write_silver_merged=AsyncMock(),
    )  # type: ignore[assignment]
    mixin.gold = SimpleNamespace(
        get_table_path=MagicMock(return_value=Path("/gold/table")),
        write_gold_merged=AsyncMock(),
    )  # type: ignore[assignment]
    mixin._COMPOSITE_GOLD_SCHEMAS = {"test.table": MagicMock()}  # type: ignore[assignment]
    return mixin


@pytest.mark.unit
def test_get_table_path_silver_default() -> None:
    """get_table_path returns silver path by default."""
    mixin = _make_mixin()
    path = mixin.get_table_path("test.table")
    assert path == Path("/silver/table")
    mixin.silver.get_table_path.assert_called_once_with("test.table")


@pytest.mark.unit
def test_get_table_path_gold() -> None:
    """get_table_path returns gold path when layer='gold'."""
    mixin = _make_mixin()
    path = mixin.get_table_path("test.table", layer="gold")
    assert path == Path("/gold/table")
    mixin.gold.get_table_path.assert_called_once_with("test.table")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_silver_delegates() -> None:
    """read_silver delegates to silver writer."""
    mixin = _make_mixin()
    result = await mixin.read_silver("test.table", columns=["id"])
    assert result == [{"id": 1}]
    mixin.silver.read_silver.assert_called_once_with("test.table", columns=["id"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_merged_delegates() -> None:
    """write_silver_merged delegates with registered core schema."""
    mixin = _make_mixin()
    records = [{"id": 1, "name": "test"}]
    await mixin.write_silver_merged(
        "test.table",
        records,
        primary_keys=["id"],
        run_id="run-1",
    )
    mixin.silver.write_silver_merged.assert_called_once_with(
        "test.table",
        records,
        ["id"],
        schema=mixin._COMPOSITE_GOLD_SCHEMAS["test.table"],
        run_id="run-1",
        sources_used=None,
        preserve_column_order=False,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_merged_unknown_table_fails_fast() -> None:
    """write_silver_merged requires a registered schema for composite paths."""
    mixin = _make_mixin()
    with pytest.raises(ValueError, match="registered validation schema"):
        await mixin.write_silver_merged("unknown.table", [{"id": 1}])
    mixin.silver.write_silver_merged.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_gold_merged_uses_composite_schema() -> None:
    """write_gold_merged looks up schema from _COMPOSITE_GOLD_SCHEMAS."""
    mixin = _make_mixin()
    records = [{"id": 1}]
    completed_at = datetime(2026, 4, 10, tzinfo=UTC)
    await mixin.write_gold_merged("test.table", records, completed_at=completed_at)
    call_kwargs = mixin.gold.write_gold_merged.call_args
    assert call_kwargs[1]["schema"] is mixin._COMPOSITE_GOLD_SCHEMAS["test.table"]
    assert call_kwargs[1]["completed_at"] == completed_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_gold_merged_unknown_table_passes_none_schema() -> None:
    """write_gold_merged fails fast for unknown Gold tables."""
    mixin = _make_mixin()
    records = [{"id": 1}]
    with pytest.raises(ValueError, match="registered strict schema"):
        await mixin.write_gold_merged("unknown.table", records)
    mixin.gold.write_gold_merged.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_gold_merged_uses_explicit_schema_for_unknown_table() -> None:
    """write_gold_merged allows an explicit strict schema at the storage seam."""
    mixin = _make_mixin()
    records = [{"id": 1}]
    schema = MagicMock()
    await mixin.write_gold_merged("unknown.table", records, schema=schema)
    call_kwargs = mixin.gold.write_gold_merged.call_args
    assert call_kwargs[1]["schema"] is schema
