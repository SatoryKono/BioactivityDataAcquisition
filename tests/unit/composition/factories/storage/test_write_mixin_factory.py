"""Unit tests for StorageBundleWriteMixin."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.storage.write_mixin import (
    StorageBundleWriteMixin,
)


def _make_mixin(
    *,
    bronze: MagicMock | None = None,
    silver: MagicMock | None = None,
    gold: MagicMock | None = None,
) -> StorageBundleWriteMixin:
    """Create a WriteMixin instance with stub writers."""
    mixin = StorageBundleWriteMixin.__new__(StorageBundleWriteMixin)
    mixin.bronze = bronze or MagicMock()  # type: ignore[assignment]
    mixin.silver = silver or MagicMock()  # type: ignore[assignment]
    mixin.gold = gold or MagicMock()  # type: ignore[assignment]
    return mixin


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_bronze_delegates() -> None:
    """write_bronze delegates to bronze.write_bronze."""
    bronze = MagicMock()
    expected = MagicMock()
    bronze.write_bronze = AsyncMock(return_value=expected)
    mixin = _make_mixin(bronze=bronze)

    result = await mixin.write_bronze(
        records=iter([b"r1"]),
        provider="chembl",
        entity="activity",
        date=MagicMock(),
        batch_id="b1",
        run_id="r1",
        run_type="incremental",
        ingestion_ts=MagicMock(),
    )

    assert result is expected
    bronze.write_bronze.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_delegates() -> None:
    """write_silver delegates to silver.write_silver."""
    silver = MagicMock()
    expected = MagicMock()
    silver.write_silver = AsyncMock(return_value=expected)
    mixin = _make_mixin(silver=silver)

    result = await mixin.write_silver(
        table_name="chembl.activity",
        records=[{"pk": 1}],
        primary_keys=["pk"],
        schema=MagicMock(),
    )

    assert result is expected
    silver.write_silver.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_gold_delegates() -> None:
    """write_gold delegates to gold.write_gold."""
    gold = MagicMock()
    gold.write_gold = AsyncMock(return_value=None)
    mixin = _make_mixin(gold=gold)

    await mixin.write_gold(
        table_name="chembl.activity",
        records=[{"pk": 1}],
        schema=MagicMock(),
    )

    gold.write_gold.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_mixin_factory__source_metadata__69a0236a() -> None:
    """source_metadata is forwarded to bronze.write_bronze."""
    bronze = MagicMock()
    bronze.write_bronze = AsyncMock(return_value=MagicMock())
    mixin = _make_mixin(bronze=bronze)
    source_meta = MagicMock()

    await mixin.write_bronze(
        records=iter([]),
        provider="chembl",
        entity="activity",
        date=MagicMock(),
        batch_id="b1",
        run_id="r1",
        run_type="incremental",
        ingestion_ts=MagicMock(),
        source_metadata=source_meta,
    )

    call_kwargs = bronze.write_bronze.call_args[1]
    assert call_kwargs["source_metadata"] is source_meta


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_passes_key_nullability_rules() -> None:
    """key_nullability_rules is forwarded to silver.write_silver."""
    silver = MagicMock()
    silver.write_silver = AsyncMock(return_value=MagicMock())
    mixin = _make_mixin(silver=silver)
    rules = [MagicMock()]

    await mixin.write_silver(
        table_name="t",
        records=[],
        primary_keys=["pk"],
        schema=MagicMock(),
        key_nullability_rules=rules,
    )

    call_kwargs = silver.write_silver.call_args[1]
    assert call_kwargs["key_nullability_rules"] is rules


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_gold_passes_scd_config() -> None:
    """scd_config is forwarded to gold.write_gold."""
    gold = MagicMock()
    gold.write_gold = AsyncMock(return_value=None)
    mixin = _make_mixin(gold=gold)
    scd = MagicMock()

    await mixin.write_gold(
        table_name="t",
        records=[],
        schema=MagicMock(),
        mode="scd2",
        scd_config=scd,
    )

    call_kwargs = gold.write_gold.call_args[1]
    assert call_kwargs["scd_config"] is scd
