"""Integration tests for SilverWriter."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.infrastructure.storage.silver_writer import SilverWriter


@pytest.fixture
def temp_delta_path(tmp_path):
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def silver_writer(temp_delta_path, noop_logger):
    return SilverWriter(base_path=temp_delta_path, logger=noop_logger)


@pytest.fixture
def sample_records():
    return [
        {
            "id": "1",
            "val": "A",
            "_run_id": "run1",
            "_run_type": "incremental",
            "_source_batch_id": "batch1",
            "_ingestion_ts": "2023-01-01T00:00:00",
        },
        {
            "id": "2",
            "val": "B",
            "_run_id": "run1",
            "_run_type": "incremental",
            "_source_batch_id": "batch1",
            "_ingestion_ts": "2023-01-01T00:00:00",
        },
    ]


@pytest.fixture
def sample_schema():
    return pa.schema(
        [
            ("id", pa.string()),
            ("val", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ]
    )


@pytest.mark.asyncio
async def test_write_silver_default_merge(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test default merge behavior."""
    await silver_writer.write_silver(
        table_name="test_table",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    dt = DeltaTable(f"{temp_delta_path}/test_table")
    assert len(dt.to_pandas()) == 2

    # Update record 1, Add record 3
    new_records = [
        {
            "id": "1",
            "val": "A_updated",
            "_run_id": "run2",
            "_run_type": "incremental",
            "_source_batch_id": "batch2",
            "_ingestion_ts": "2023-01-02T00:00:00",
        },
        {
            "id": "3",
            "val": "C",
            "_run_id": "run2",
            "_run_type": "incremental",
            "_source_batch_id": "batch2",
            "_ingestion_ts": "2023-01-02T00:00:00",
        },
    ]

    await silver_writer.write_silver(
        table_name="test_table",
        records=new_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    # Reload Delta Table to see changes
    dt = DeltaTable(f"{temp_delta_path}/test_table")
    df = dt.to_pandas().sort_values("id")
    assert len(df) == 3
    assert df.loc[df["id"] == "1", "val"].iloc[0] == "A_updated"
    assert df.loc[df["id"] == "2", "val"].iloc[0] == "B"
    assert df.loc[df["id"] == "3", "val"].iloc[0] == "C"


@pytest.mark.asyncio
async def test_write_silver_append_mode(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test append mode (duplicates allowed)."""
    await silver_writer.write_silver(
        table_name="test_append",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="append",
    )

    # Append same records again
    await silver_writer.write_silver(
        table_name="test_append",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="append",
    )

    dt = DeltaTable(f"{temp_delta_path}/test_append")
    assert len(dt.to_pandas()) == 4  # Should be doubled


@pytest.mark.asyncio
async def test_write_silver_delete_mode(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test delete mode (replaces all existing data)."""
    # Silver layer does not support 'delete' mode (overwrite).
    # It only supports 'append' and 'merge'.
    # This test verifies that PolicyViolationError is raised.
    from bioetl.domain.exceptions import PolicyViolationError

    with pytest.raises(PolicyViolationError, match="silver does not allow overwrite"):
        await silver_writer.write_silver(
            table_name="test_overwrite",
            records=sample_records,
            primary_keys=["id"],
            schema=sample_schema,
            mode="delete",
        )


@pytest.mark.asyncio
async def test_write_silver_partitioning(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test partitioning."""
    # Silver layer does not support 'delete' mode, so we use 'append' for partitioning test
    await silver_writer.write_silver(
        table_name="test_partition",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="append",
        partition_cols=["val"],
    )

    base_path = Path(temp_delta_path) / "test_partition"
    assert (base_path / "val=A").exists()
    assert (base_path / "val=B").exists()


@pytest.mark.asyncio
async def test_read_silver_returns_records(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test read_silver returns records from existing table."""
    # First write some records
    await silver_writer.write_silver(
        table_name="test_read",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    # Then read them back
    records = await silver_writer.read_silver("test_read")

    assert len(records) == 2
    assert any(r["id"] == "1" and r["val"] == "A" for r in records)
    assert any(r["id"] == "2" and r["val"] == "B" for r in records)


@pytest.mark.asyncio
async def test_read_silver_with_columns(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test read_silver with column selection."""
    await silver_writer.write_silver(
        table_name="test_read_cols",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    # Read only specific columns
    records = await silver_writer.read_silver("test_read_cols", columns=["id", "val"])

    assert len(records) == 2
    # Should only have selected columns
    assert set(records[0].keys()) == {"id", "val"}


@pytest.mark.asyncio
async def test_read_silver_table_not_found(silver_writer):
    """Test read_silver raises FileNotFoundError for missing table."""
    with pytest.raises(FileNotFoundError, match="Table not found"):
        await silver_writer.read_silver("nonexistent_table")


@pytest.mark.asyncio
async def test_write_silver_merged_creates_table(silver_writer, temp_delta_path):
    """Test write_silver_merged creates table with inferred schema."""
    records = [
        {"id": "1", "name": "Test1", "value": 100},
        {"id": "2", "name": "Test2", "value": 200},
    ]

    await silver_writer.write_silver_merged(
        table_name="test_merged",
        records=records,
        primary_keys=["id"],
    )

    # Verify table was created
    dt = DeltaTable(f"{temp_delta_path}/test_merged")
    df = dt.to_pandas()
    assert len(df) == 2
    assert set(df.columns) == {"id", "name", "value"}


@pytest.mark.asyncio
async def test_write_silver_merged_overwrites_existing(silver_writer, temp_delta_path):
    """Test write_silver_merged overwrites existing data."""
    # Write initial records
    await silver_writer.write_silver_merged(
        table_name="test_merged_overwrite",
        records=[{"id": "1", "val": "A"}],
    )

    # Overwrite with new records
    await silver_writer.write_silver_merged(
        table_name="test_merged_overwrite",
        records=[{"id": "2", "val": "B"}, {"id": "3", "val": "C"}],
    )

    # Should only have new records
    dt = DeltaTable(f"{temp_delta_path}/test_merged_overwrite")
    df = dt.to_pandas()
    assert len(df) == 2
    assert set(df["id"]) == {"2", "3"}


@pytest.mark.asyncio
async def test_write_silver_merged_empty_records(silver_writer, noop_logger):
    """Test write_silver_merged handles empty records gracefully."""
    # Should not raise, just log warning
    await silver_writer.write_silver_merged(
        table_name="test_empty",
        records=[],
    )
