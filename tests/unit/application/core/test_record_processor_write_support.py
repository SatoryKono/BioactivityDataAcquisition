# pyright: reportArgumentType=false

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._record_processor_write_support import (
    write_gold_layer,
    write_silver_layer,
)
from bioetl.application.core.batch_processing_contracts import LayerWriteOutcome
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.types import BatchID

pytestmark = pytest.mark.unit


@pytest.fixture
def span_executor():
    executor = MagicMock()
    async def execute_with_span(name, coro, batch_id, count, *, on_error=None):
        try:
            return await coro
        except Exception as e:
            if on_error:
                on_error(e)
            raise
    executor.execute_with_span = AsyncMock(side_effect=execute_with_span)
    return executor


@pytest.fixture
def writer():
    w = MagicMock()
    w.write_silver = AsyncMock(return_value="silver_ref")
    w.write_gold = AsyncMock(return_value="gold_ref")
    w.log_and_track_write_error = MagicMock()
    return w


@pytest.mark.asyncio
async def test_write_silver_layer_skipped(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[], quarantined_count=0)
    outcome = await write_silver_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=None,
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
    )
    assert outcome.layer == "silver"
    assert outcome.status == "skipped"


@pytest.mark.asyncio
async def test_write_silver_layer_without_quarantine(span_executor, writer):
    result = TransformResult(silver_records=[{"id": 1}], gold_records=[], quarantined_count=0)
    outcome = await write_silver_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=None,
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
    )
    assert outcome.layer == "silver"
    assert outcome.status == "written"
    assert outcome.candidate_count == 1
    assert outcome.confirmed_count == 1
    assert outcome.write_result == "silver_ref"


@pytest.mark.asyncio
async def test_write_silver_layer_without_quarantine_error(span_executor, writer):
    result = TransformResult(silver_records=[{"id": 1}], gold_records=[], quarantined_count=0)
    writer.write_silver = AsyncMock(side_effect=RuntimeError("write error"))
    with pytest.raises(RuntimeError, match="write error"):
        await write_silver_layer(
            span_executor=span_executor,
            writer=writer,
            quarantine_manager=None,
            logger=MagicMock(),
            run_id=None,
            domain_event_emitter=None,
            result=result,
            batch_id=BatchID("batch-1"),
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            bronze_refs=None,
        )
    writer.log_and_track_write_error.assert_called_once()


@pytest.mark.asyncio
async def test_write_silver_layer_with_quarantine(span_executor, writer):
    result = TransformResult(silver_records=[{"id": 1}], gold_records=[], quarantined_count=0)
    outcome = await write_silver_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=MagicMock(),
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
    )
    assert outcome.layer == "silver"


@pytest.mark.asyncio
async def test_write_gold_layer_skipped(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[], quarantined_count=0)
    outcome = await write_gold_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=None,
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        silver_outcome=LayerWriteOutcome(layer="silver", status="skipped", candidate_count=0),
    )
    assert outcome.layer == "gold"
    assert outcome.status == "skipped"


@pytest.mark.asyncio
async def test_write_gold_layer_blocked(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[{"id": 1}], quarantined_count=0)
    outcome = await write_gold_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=None,
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        silver_outcome=LayerWriteOutcome(layer="silver", status="quarantined", candidate_count=1),
    )
    assert outcome.layer == "gold"
    assert outcome.status == "blocked"


@pytest.mark.asyncio
async def test_write_gold_layer_without_quarantine(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[{"id": 1}], quarantined_count=0)
    outcome = await write_gold_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=None,
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        silver_outcome=LayerWriteOutcome(layer="silver", status="written", candidate_count=1, write_result="silver_ref"),
    )
    assert outcome.layer == "gold"
    assert outcome.status == "written"
    assert outcome.candidate_count == 1
    assert outcome.confirmed_count == 1


@pytest.mark.asyncio
async def test_write_gold_layer_without_quarantine_error(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[{"id": 1}], quarantined_count=0)
    writer.write_gold = AsyncMock(side_effect=RuntimeError("write error"))
    with pytest.raises(RuntimeError, match="write error"):
        await write_gold_layer(
            span_executor=span_executor,
            writer=writer,
            quarantine_manager=None,
            logger=MagicMock(),
            run_id=None,
            domain_event_emitter=None,
            result=result,
            batch_id=BatchID("batch-1"),
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            silver_outcome=LayerWriteOutcome(layer="silver", status="written", candidate_count=1, write_result="silver_ref"),
        )
    writer.log_and_track_write_error.assert_called_once()


@pytest.mark.asyncio
async def test_write_gold_layer_with_quarantine(span_executor, writer):
    result = TransformResult(silver_records=[], gold_records=[{"id": 1}], quarantined_count=0)
    outcome = await write_gold_layer(
        span_executor=span_executor,
        writer=writer,
        quarantine_manager=MagicMock(),
        logger=MagicMock(),
        run_id=None,
        domain_event_emitter=None,
        result=result,
        batch_id=BatchID("batch-1"),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        silver_outcome=LayerWriteOutcome(layer="silver", status="written", candidate_count=1, write_result="silver_ref"),
    )
    assert outcome.layer == "gold"
