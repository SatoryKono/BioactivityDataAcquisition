"""Tests for RetentionPolicy.deduplicate_silver."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake

from bioetl.infrastructure.storage.retention_manager import RetentionPolicy


@pytest.fixture
def tmp_delta_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for Delta tables."""
    return tmp_path / "silver"


def _write_test_table(
    table_dir: Path,
    records: list[dict],
    mode: str = "append",
) -> None:
    """Write records to a Delta table."""
    table_dir.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )
    arrays = [
        pa.array([r["activity_id"] for r in records]),
        pa.array([r["value"] for r in records]),
        pa.array([r["_ingestion_ts"] for r in records]),
    ]
    table = pa.table(arrays, schema=schema)
    write_deltalake(str(table_dir), table, mode=mode)


@pytest.mark.asyncio
async def test_deduplicate_removes_duplicates(tmp_delta_dir: Path) -> None:
    """Dedup should keep latest record per PK."""
    table_path = tmp_delta_dir / "test_entity"

    # Write batch 1 (older)
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 10.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
            {
                "activity_id": "2",
                "value": 20.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
        ],
    )
    # Append batch 2 (newer, with duplicate for id=1)
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 15.0,
                "_ingestion_ts": "2024-01-02T00:00:00Z",
            },
            {
                "activity_id": "3",
                "value": 30.0,
                "_ingestion_ts": "2024-01-02T00:00:00Z",
            },
        ],
        mode="append",
    )

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 1  # One duplicate for activity_id=1

    # Verify the table has 3 unique records
    from deltalake import DeltaTable

    dt = DeltaTable(str(table_path))
    result = dt.to_pyarrow_table()
    assert result.num_rows == 3

    # Verify the latest value for activity_id=1 is kept
    rows = result.to_pylist()
    id1_rows = [r for r in rows if r["activity_id"] == "1"]
    assert len(id1_rows) == 1
    assert id1_rows[0]["value"] == 15.0  # Latest value


@pytest.mark.asyncio
async def test_deduplicate_no_duplicates(tmp_delta_dir: Path) -> None:
    """Dedup should return 0 when no duplicates exist."""
    table_path = tmp_delta_dir / "test_entity"
    _write_test_table(
        table_path,
        [
            {
                "activity_id": "1",
                "value": 10.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
            {
                "activity_id": "2",
                "value": 20.0,
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            },
        ],
    )

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 0


@pytest.mark.asyncio
async def test_deduplicate_empty_table(tmp_delta_dir: Path) -> None:
    """Dedup should return 0 for empty table."""
    table_path = tmp_delta_dir / "test_entity"
    table_path.mkdir(parents=True, exist_ok=True)

    schema = pa.schema(
        [
            pa.field("activity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )
    empty = pa.table(
        [
            pa.array([], type=pa.string()),
            pa.array([], type=pa.float64()),
            pa.array([], type=pa.string()),
        ],
        schema=schema,
    )
    write_deltalake(str(table_path), empty)

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))
    removed = await mgr.deduplicate_silver("test_entity", primary_keys=["activity_id"])

    assert removed == 0


@pytest.mark.asyncio
async def test_deduplicate_missing_table(tmp_delta_dir: Path) -> None:
    """Dedup should raise TableNotFoundError for missing table."""
    from bioetl.domain.exceptions import TableNotFoundError

    mgr = RetentionPolicy(base_path=str(tmp_delta_dir))

    with pytest.raises(TableNotFoundError):
        await mgr.deduplicate_silver("nonexistent", primary_keys=["activity_id"])
