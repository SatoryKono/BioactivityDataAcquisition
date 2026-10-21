"""The merged-output boundary independently checks storage commit receipts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import polars as pl
import pytest

from bioetl.application.composite import merger_output_mixin
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "receipt, error, message",
    [
        ({}, TypeError, "GoldWriteReceipt"),
        (
            GoldWriteReceipt("table", "1", GoldWriteCategory.UNKNOWN),
            GoldWriteFailure,
            "UNKNOWN",
        ),
        (
            GoldWriteReceipt("other", "1", GoldWriteCategory.COMPLETE),
            TypeError,
            "requested table",
        ),
    ],
)
async def test_merged_writer_rejects_invalid_receipt_even_with_pass_through_observer(
    monkeypatch, receipt, error, message
):
    async def observe(operation, count):
        return await operation

    monkeypatch.setattr(merger_output_mixin, "observe_gold_write", observe)
    writer = merger_output_mixin.MergeOutputWriterMixin()
    writer._field_group_registry = None
    writer._gold_schema = object()
    writer._config = SimpleNamespace(output_gold_path="gold/table")
    writer._logger = Mock()
    writer._storage = SimpleNamespace(write_gold_merged=AsyncMock(return_value=receipt))
    frame = pl.DataFrame({"id": [1]})
    with pytest.raises(error, match=message):
        await writer._write_merged_gold(frame)
    writer._storage.write_gold_merged.assert_awaited_once()
    assert frame.to_dicts() == [{"id": 1}]
