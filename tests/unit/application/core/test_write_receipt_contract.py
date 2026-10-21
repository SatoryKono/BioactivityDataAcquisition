"""Write accounting requires complete Gold receipts and durable Silver success."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.application.core._batch_write_support import (
    LayerWriteContext,
    LayerWriteOutcome,
    safe_write_layer,
)
from bioetl.application.core._record_processor_write_support import (
    write_gold_layer,
    write_silver_layer,
)
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt

pytestmark = pytest.mark.unit


async def _execute_span(name, pending, *args, **kwargs):
    return await pending


def _writer():
    return Mock(
        write_silver=AsyncMock(return_value=None),
        write_gold=AsyncMock(
            return_value=GoldWriteReceipt("table", "1", GoldWriteCategory.COMPLETE)
        ),
    )


@pytest.mark.asyncio
async def test_incomplete_gold_does_not_confirm_or_quarantine_committed_rows():
    receipt = GoldWriteReceipt(
        "table", "1", GoldWriteCategory.COMMITTED_POSTWRITE_PENDING, ("table",)
    )
    writer = _writer()
    writer.write_gold.return_value = receipt
    quarantine = Mock()
    context = LayerWriteContext(_execute_span, writer, quarantine, Mock(), None, None)
    with pytest.raises(GoldWriteFailure) as caught:
        await safe_write_layer(
            context=context,
            layer="gold",
            records=[{"id": 1}],
            batch_id="batch",
            ingestion_ts=datetime(2026, 10, 21, tzinfo=UTC),
            bronze_refs=None,
            operation_errors=(RuntimeError,),
        )
    assert caught.value.receipt is receipt
    writer.track_batch_written.assert_not_called()
    quarantine.assert_not_called()


@pytest.mark.asyncio
async def test_record_processor_quarantine_path_preserves_successful_layer_counts():
    writer = _writer()
    result = SimpleNamespace(silver_records=[{"id": 1}], gold_records=[{"id": 1}])
    common = {
        "span_executor": SimpleNamespace(execute_with_span=_execute_span),
        "writer": writer,
        "quarantine_manager": Mock(),
        "logger": Mock(),
        "run_id": None,
        "domain_event_emitter": None,
        "result": result,
        "batch_id": "batch",
        "ingestion_ts": datetime(2026, 10, 21, tzinfo=UTC),
    }
    silver = await write_silver_layer(**common, bronze_refs=None)
    gold = await write_gold_layer(**common, silver_outcome=silver)
    assert (silver.status, silver.confirmed_count) == ("written", 1)
    assert (gold.status, gold.confirmed_count) == ("written", 1)
    writer.write_silver.assert_awaited_once()
    writer.write_gold.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_gold_never_invokes_writer_even_after_silver_success():
    writer = _writer()
    result = await write_gold_layer(
        span_executor=SimpleNamespace(execute_with_span=_execute_span),
        writer=writer,
        quarantine_manager=Mock(),
        logger=Mock(),
        run_id=None,
        domain_event_emitter=None,
        result=SimpleNamespace(gold_records=[]),
        batch_id="batch",
        ingestion_ts=datetime(2026, 10, 21, tzinfo=UTC),
        silver_outcome=LayerWriteOutcome("silver", "written", 1, confirmed_count=1),
    )
    assert (result.status, result.confirmed_count) == ("skipped", 0)
    writer.write_gold.assert_not_called()
