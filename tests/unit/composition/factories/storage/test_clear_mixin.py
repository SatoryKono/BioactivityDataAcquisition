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
"""Unit tests for StorageBundleClearMixin."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.storage.clear_mixin import (
    StorageBundleClearMixin,
)


def _make_mixin(
    *,
    silver_clear_return: int = 3,
    gold_clear_return: int = 2,
    silver_csv_exporter: MagicMock | None = None,
    gold_csv_exporter: MagicMock | None = None,
) -> StorageBundleClearMixin:
    """Create a ClearMixin instance with stub writers."""
    silver = SimpleNamespace(
        clear=MagicMock(return_value=silver_clear_return),
        csv_exporter=silver_csv_exporter,
    )
    gold = SimpleNamespace(
        clear=MagicMock(return_value=gold_clear_return),
        csv_exporter=gold_csv_exporter,
    )
    mixin = StorageBundleClearMixin.__new__(StorageBundleClearMixin)
    mixin.silver = silver  # type: ignore[assignment]
    mixin.gold = gold  # type: ignore[assignment]
    return mixin


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_silver_delegates_to_writer() -> None:
    """clear_silver delegates to _run_clear with silver writer."""
    mixin = _make_mixin(silver_clear_return=5)
    result = await mixin.clear_silver("chembl.activity")
    assert result == 5
    mixin.silver.clear.assert_called_once_with("chembl.activity", dry_run=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_silver_dry_run() -> None:
    """clear_silver passes dry_run flag through."""
    mixin = _make_mixin(silver_clear_return=0)
    result = await mixin.clear_silver("chembl.activity", dry_run=True)
    assert result == 0
    mixin.silver.clear.assert_called_once_with("chembl.activity", dry_run=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_silver_with_csv_exporter() -> None:
    """clear_silver also clears CSV export when exporter is configured."""
    csv_exporter = MagicMock()
    csv_exporter.clear = MagicMock(return_value=["file1.csv", "file2.csv"])
    mixin = _make_mixin(silver_clear_return=3, silver_csv_exporter=csv_exporter)
    result = await mixin.clear_silver("chembl.activity")
    assert result == 5  # 3 delta + 2 csv
    csv_exporter.clear.assert_called_once_with("chembl.activity")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_gold_delegates_to_writer() -> None:
    """clear_gold delegates to _run_clear with gold writer."""
    mixin = _make_mixin(gold_clear_return=7)
    result = await mixin.clear_gold("chembl.activity")
    assert result == 7
    mixin.gold.clear.assert_called_once_with("chembl.activity", dry_run=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_gold_with_csv_exporter() -> None:
    """clear_gold also clears CSV export when exporter is configured."""
    csv_exporter = MagicMock()
    csv_exporter.clear = MagicMock(return_value=["g1.csv"])
    mixin = _make_mixin(gold_clear_return=2, gold_csv_exporter=csv_exporter)
    result = await mixin.clear_gold("chembl.activity")
    assert result == 3  # 2 delta + 1 csv
    csv_exporter.clear.assert_called_once_with("chembl.activity")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_csv_both_layers() -> None:
    """clear_csv clears CSV exports from both Silver and Gold."""
    silver_csv = MagicMock()
    silver_csv.clear = MagicMock(return_value=["s1.csv", "s2.csv"])
    gold_csv = MagicMock()
    gold_csv.clear = MagicMock(return_value=["g1.csv"])
    mixin = _make_mixin(silver_csv_exporter=silver_csv, gold_csv_exporter=gold_csv)
    result = await mixin.clear_csv("chembl.activity")
    assert result == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_csv_no_exporters() -> None:
    """clear_csv returns 0 when no exporters configured."""
    mixin = _make_mixin()
    result = await mixin.clear_csv("chembl.activity")
    assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_csv_integer_return() -> None:
    """clear_csv handles integer return values from exporter.clear."""
    silver_csv = MagicMock()
    silver_csv.clear = MagicMock(return_value=4)
    mixin = _make_mixin(silver_csv_exporter=silver_csv)
    result = await mixin.clear_csv("table")
    assert result == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_delta_with_table_name() -> None:
    """clear_delta clears specific table from both layers."""
    mixin = _make_mixin(silver_clear_return=1, gold_clear_return=1)
    result = await mixin.clear_delta("chembl.activity")
    assert result == 2
    mixin.silver.clear.assert_called_once_with("chembl.activity")
    mixin.gold.clear.assert_called_once_with("chembl.activity")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_delta_without_table_name() -> None:
    """clear_delta returns 0 when no table_name given."""
    mixin = _make_mixin()
    result = await mixin.clear_delta(None)
    assert result == 0
