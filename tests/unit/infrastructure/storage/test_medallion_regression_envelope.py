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
"""Medallion regression envelope for Bronze and Silver storage invariants."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from tests.helpers.deterministic_ids import deterministic_batch_id, deterministic_run_id


def _batch_id(label: str) -> BatchID:
    return BatchID(deterministic_batch_id(f"medallion.regression.{label}"))


def _run_id(label: str) -> RunID:
    return RunID(deterministic_run_id(f"medallion.regression.{label}"))


async def _read_bronze_payloads(writer: BronzeWriter, relative_path: str) -> list[dict]:
    payloads = []
    async for payload in writer.read_bronze(relative_path):
        payloads.append(payload)
    return payloads


def _meta_path(tmp_path: Path, relative_path: str) -> Path:
    return (tmp_path / relative_path).with_suffix(".zst.meta.json")


def _json_copy_path(tmp_path: Path, relative_path: str) -> Path:
    return (tmp_path / relative_path).with_suffix("")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bronze_append_only_writes_keep_prior_batches_readable(
    tmp_path: Path,
) -> None:
    """A later Bronze batch must not rewrite or hide an earlier raw batch."""
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    date = datetime(2024, 1, 15, tzinfo=UTC)
    ingestion_ts = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)

    first = await writer.write_bronze(
        records=iter([b'{"id": 1, "name": "first"}\n']),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=_batch_id("append.first"),
        run_id=_run_id("append"),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )
    first_file_bytes = (tmp_path / first.relative_path).read_bytes()

    second = await writer.write_bronze(
        records=iter([b'{"id": 2, "name": "second"}\n']),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=_batch_id("append.second"),
        run_id=_run_id("append"),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )

    listed_batches = await writer.list_batches("chembl", "activity", date=date)

    assert first.relative_path != second.relative_path
    assert sorted(listed_batches) == sorted([first.relative_path, second.relative_path])
    assert (tmp_path / first.relative_path).read_bytes() == first_file_bytes
    assert await _read_bronze_payloads(writer, first.relative_path) == [
        {"id": 1, "name": "first"}
    ]
    assert await _read_bronze_payloads(writer, second.relative_path) == [
        {"id": 2, "name": "second"}
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bronze_write_captures_raw_payload_before_caller_mutation(
    tmp_path: Path,
) -> None:
    """Caller-owned record containers must not mutate persisted raw Bronze data."""
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    date = datetime(2024, 1, 15, tzinfo=UTC)
    ingestion_ts = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    records = [
        b'{"id": 1, "name": "original"}\n',
        b'{"id": 2, "name": "stable"}\n',
    ]

    result = await writer.write_bronze(
        records=iter(records),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=_batch_id("immutable-payload"),
        run_id=_run_id("immutable-payload"),
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )
    records[0] = b'{"id": 1, "name": "mutated"}\n'

    assert await _read_bronze_payloads(writer, result.relative_path) == [
        {"id": 1, "name": "original"},
        {"id": 2, "name": "stable"},
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bronze_same_batch_retry_with_same_payload_is_noop(
    tmp_path: Path,
) -> None:
    """Same batch retries may succeed only when raw data and metadata are identical."""
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    date = datetime(2024, 1, 15, tzinfo=UTC)
    ingestion_ts = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    batch_id = _batch_id("same-batch-retry")
    run_id = _run_id("same-batch-retry")
    records = [
        b'{"id": 1, "name": "stable"}\n',
        b'{"id": 2, "name": "retry-safe"}\n',
    ]

    first = await writer.write_bronze(
        records=iter(records),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=batch_id,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )
    first_data_bytes = (tmp_path / first.relative_path).read_bytes()
    first_meta_bytes = _meta_path(tmp_path, first.relative_path).read_bytes()
    first_json_bytes = _json_copy_path(tmp_path, first.relative_path).read_bytes()

    second = await writer.write_bronze(
        records=iter(records),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=batch_id,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )

    listed_batches = await writer.list_batches("chembl", "activity", date=date)
    assert second.relative_path == first.relative_path
    assert listed_batches == [first.relative_path]
    assert (tmp_path / first.relative_path).read_bytes() == first_data_bytes
    assert _meta_path(tmp_path, first.relative_path).read_bytes() == first_meta_bytes
    assert (
        _json_copy_path(tmp_path, first.relative_path).read_bytes() == first_json_bytes
    )
    assert await _read_bronze_payloads(writer, first.relative_path) == [
        {"id": 1, "name": "stable"},
        {"id": 2, "name": "retry-safe"},
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bronze_same_batch_retry_with_different_payload_is_rejected(
    tmp_path: Path,
) -> None:
    """Same batch retries must not replace immutable raw Bronze payloads."""
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    date = datetime(2024, 1, 15, tzinfo=UTC)
    ingestion_ts = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    batch_id = _batch_id("same-batch-conflict")
    run_id = _run_id("same-batch-conflict")

    first = await writer.write_bronze(
        records=iter([b'{"id": 1, "name": "original"}\n']),
        provider="chembl",
        entity="activity",
        date=date,
        batch_id=batch_id,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        ingestion_ts=ingestion_ts,
    )
    first_data_bytes = (tmp_path / first.relative_path).read_bytes()
    first_meta_bytes = _meta_path(tmp_path, first.relative_path).read_bytes()
    first_json_bytes = _json_copy_path(tmp_path, first.relative_path).read_bytes()

    with pytest.raises(FileExistsError):
        await writer.write_bronze(
            records=iter([b'{"id": 1, "name": "mutated"}\n']),
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=ingestion_ts,
        )

    assert (tmp_path / first.relative_path).read_bytes() == first_data_bytes
    assert _meta_path(tmp_path, first.relative_path).read_bytes() == first_meta_bytes
    assert (
        _json_copy_path(tmp_path, first.relative_path).read_bytes() == first_json_bytes
    )
    assert await _read_bronze_payloads(writer, first.relative_path) == [
        {"id": 1, "name": "original"},
    ]
