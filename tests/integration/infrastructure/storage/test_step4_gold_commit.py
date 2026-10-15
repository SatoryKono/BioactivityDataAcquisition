"""Real temporary Delta receipts with synthetic records only."""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import AsyncMock
import pandera.pandas as pa
import pytest
from deltalake import DeltaTable
from bioetl.domain.exceptions.base_exceptions import BioETLDomainError
from bioetl.domain.exceptions.gold_write import GoldWriteFailure
from bioetl.infrastructure.storage.gold.commit_outcome import GoldWriteCancelled
from bioetl.domain.types.gold_contracts import GoldWriteCategory as Category
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
import bioetl.infrastructure.storage.gold_writer as module

pytestmark = pytest.mark.integration


@pytest.fixture
def writer(tmp_path):
    return GoldWriter(
        tmp_path / "gold",
        NoOpLogger(),
        runtime_services=build_gold_writer_runtime_services(
            csv_exporter=None,
            tracing=None,
            metrics=None,
            audit=None,
            metadata_writer=None,
            metadata_coordinator=None,
            lineage_store=None,
        ),
    )


@pytest.fixture
def schema():
    return pa.DataFrameSchema(
        {"entity_id": pa.Column(str), "value": pa.Column(float)}, strict=True
    )


RECORDS = [{"entity_id": "synthetic-one", "value": 1.0}]


def rows(writer):
    return (
        DeltaTable(str(writer.get_table_path("test.activity")))
        .to_pyarrow_table()
        .to_pylist()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["csv", "metadata", "cancel_after"])
async def test_real_postcommit_failure_preserves_commit(writer, schema, stage):
    original = (
        asyncio.CancelledError("synthetic")
        if stage == "cancel_after"
        else BioETLDomainError("synthetic publication failure")
    )
    if stage == "csv":
        writer.csv_exporter = type(
            "Exporter", (), {"export": AsyncMock(side_effect=original)}
        )()
    else:
        writer._post_write_gold = AsyncMock(side_effect=original)
    wrapper = GoldWriteCancelled if stage == "cancel_after" else GoldWriteFailure
    with pytest.raises(wrapper) as found:
        await writer.write_gold("test.activity", RECORDS, schema, mode="append")
    assert found.value.__cause__ is original
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert found.value.receipt.committed_targets == ("test.activity",)
    assert rows(writer) == RECORDS
    assert DeltaTable(str(writer.get_table_path("test.activity"))).version() == 0


@pytest.mark.asyncio
async def test_cancel_during_real_write_drains_committed_thread(
    writer, schema, monkeypatch
):
    started = threading.Event()
    finish = threading.Event()
    original_write = module.write_deltalake
    calls = []

    def blocked(*args, **kwargs):
        calls.append(1)
        started.set()
        assert finish.wait(10)
        return original_write(*args, **kwargs)

    monkeypatch.setattr(module, "write_deltalake", blocked)
    writer._post_write_gold = AsyncMock()
    task = asyncio.create_task(
        writer.write_gold("test.activity", RECORDS, schema, mode="append")
    )
    assert await asyncio.to_thread(started.wait, 5)
    task.cancel()
    finish.set()
    with pytest.raises(GoldWriteCancelled) as found:
        await task
    assert task.cancelled()
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert calls == [1] and rows(writer) == RECORDS
    writer._post_write_gold.assert_not_awaited()


@pytest.mark.asyncio
async def test_error_after_possible_commit_is_unknown_and_never_retried(
    writer, schema, monkeypatch
):
    original_write = module.write_deltalake
    calls = []

    def ambiguous(*args, **kwargs):
        calls.append(1)
        original_write(*args, **kwargs)
        raise OSError("synthetic ambiguous return")

    monkeypatch.setattr(module, "write_deltalake", ambiguous)
    with pytest.raises(GoldWriteFailure) as found:
        await writer.write_gold("test.activity", RECORDS, schema, mode="append")
    assert found.value.receipt.category == Category.UNKNOWN
    assert found.value.receipt.committed_targets == ()
    assert calls == [1] and rows(writer) == RECORDS


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["csv", "metadata"])
async def test_merged_gold_retains_postcommit_receipt(
    writer, schema, stage, monkeypatch
):
    from bioetl.infrastructure.storage.gold import io_execution

    original = BioETLDomainError("synthetic merged publication")
    target = (
        "_export_gold_merged_csv" if stage == "csv" else "_write_gold_merged_sidecar"
    )
    monkeypatch.setattr(io_execution, target, AsyncMock(side_effect=original))
    with pytest.raises(GoldWriteFailure) as found:
        await writer.write_gold_merged("test.activity", RECORDS, schema=schema)
    assert found.value.receipt.category == Category.COMMITTED_POSTWRITE_PENDING
    assert found.value.__cause__ is original
    assert rows(writer) == RECORDS
