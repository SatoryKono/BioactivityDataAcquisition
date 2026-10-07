# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression for #12119: quarantine reads vs table partition layout.

Fresh quarantine tables are created partitioned by ``pipeline``; legacy
tables may exist without partitioning. All read surfaces (inspect, replay,
purge, stats) must work on both layouts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.types import BatchID, QuarantineRecordStatus
from bioetl.infrastructure.quarantine.unified import (
    UnifiedQuarantineAdapter,
    _normalize_quarantine_record,
)

pytestmark = pytest.mark.integration

INGESTION_TS = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)
BATCH_ID = BatchID(UUID("12345678-1234-5678-1234-567812345678"))


def _request(pipeline: str, record_id: int, **overrides):
    return {
        "pipeline": pipeline,
        "error_code": "SCHEMA_VIOLATION",
        "payload": {"id": record_id},
        "bronze_batch_id": BATCH_ID,
        "run_id": None,
        "metadata": {"error_details": {"reason": "test"}},
        "ingestion_ts": INGESTION_TS,
        **overrides,
    }


def _write_legacy_nonpartitioned(base_path: str, records: list[dict]) -> None:
    """Simulate a legacy quarantine table created without partitioning."""
    normalized = [_normalize_quarantine_record(record) for record in records]
    write_deltalake(
        table_or_uri=base_path,
        data=pa.Table.from_pylist(normalized),
        mode="append",
    )


async def test_fresh_write_creates_pipeline_partitioned_table(tmp_path) -> None:
    """Canonical write path must create a pipeline-partitioned table."""
    adapter = UnifiedQuarantineAdapter(str(tmp_path / "quarantine"))

    await adapter.write_many([_request("pipe_a", 1), _request("pipe_b", 2)])

    dt = DeltaTable(str(tmp_path / "quarantine"))
    assert list(dt.metadata().partition_columns) == ["pipeline"]


async def test_inspect_roundtrip_on_fresh_table(tmp_path) -> None:
    """inspect must not raise and must filter by pipeline on a fresh table."""
    adapter = UnifiedQuarantineAdapter(str(tmp_path / "quarantine"))
    await adapter.write_many([_request("pipe_a", 1), _request("pipe_b", 2)])

    records = await adapter.inspect(pipeline="pipe_a")

    assert len(records) == 1
    assert records[0]["pipeline"] == "pipe_a"
    assert records[0]["payload"] == {"id": 1}


async def test_repeated_appends_keep_inspect_working(tmp_path) -> None:
    """Second append must keep the partitioned layout and stay readable."""
    adapter = UnifiedQuarantineAdapter(str(tmp_path / "quarantine"))
    await adapter.write_many([_request("pipe_a", 1)])
    await adapter.write_many([_request("pipe_a", 2)])

    records = await adapter.inspect(pipeline="pipe_a")

    assert {record["payload"]["id"] for record in records} == {1, 2}


async def test_inspect_reads_legacy_nonpartitioned_table(tmp_path) -> None:
    """Legacy tables without partitions must still be inspectable."""
    base_path = str(tmp_path / "quarantine")
    _write_legacy_nonpartitioned(
        base_path, [_request("pipe_a", 1), _request("pipe_b", 2)]
    )

    adapter = UnifiedQuarantineAdapter(base_path)
    records = await adapter.inspect(pipeline="pipe_a")

    assert len(records) == 1
    assert records[0]["pipeline"] == "pipe_a"


async def test_replay_and_purge_on_legacy_nonpartitioned_table(tmp_path) -> None:
    """replay/purge must not crash on legacy tables without partitions."""
    base_path = str(tmp_path / "quarantine")
    old_ts = INGESTION_TS - timedelta(days=60)
    _write_legacy_nonpartitioned(
        base_path,
        [
            _request("pipe_a", 1),
            _request("pipe_a", 2, ingestion_ts=old_ts),
            _request("pipe_b", 3, ingestion_ts=old_ts),
        ],
    )
    adapter = UnifiedQuarantineAdapter(base_path)

    replayed = list(adapter.replay("pipe_a", now=INGESTION_TS))
    assert {record["payload"]["id"] for record in replayed} == {1, 2}

    purged = adapter.purge("pipe_a", older_than_days=30, now=INGESTION_TS)
    assert purged == 1

    stats = await adapter.get_stats("pipe_a")
    assert stats["total_records"] == 1

    remaining = await adapter.inspect(pipeline="pipe_b")
    assert len(remaining) == 1
    assert remaining[0]["dq_status"] == QuarantineRecordStatus.NEW.value
