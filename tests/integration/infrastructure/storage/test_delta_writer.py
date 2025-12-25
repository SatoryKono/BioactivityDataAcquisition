"""Integration tests for DeltaWriter."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


@pytest.fixture
def noop_logger():
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


@pytest.fixture
def temp_delta_path(tmp_path):
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def delta_writer(temp_delta_path, noop_logger):
    return DeltaWriter(base_path=temp_delta_path, logger=noop_logger)


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
    delta_writer, temp_delta_path, sample_records, sample_schema
):
    """Test default merge behavior."""
    await delta_writer.write_silver(
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

    await delta_writer.write_silver(
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
    delta_writer, temp_delta_path, sample_records, sample_schema
):
    """Test append mode (duplicates allowed)."""
    await delta_writer.write_silver(
        table_name="test_append",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="append",
    )

    # Append same records again
    await delta_writer.write_silver(
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
    delta_writer, temp_delta_path, sample_records, sample_schema
):
    """Test delete mode (replaces all existing data)."""
    await delta_writer.write_silver(
        table_name="test_overwrite",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    new_records = [
        {
            "id": "3",
            "val": "C",
            "_run_id": "run3",
            "_run_type": "incremental",
            "_source_batch_id": "batch3",
            "_ingestion_ts": "2023-01-03T00:00:00",
        }
    ]

    await delta_writer.write_silver(
        table_name="test_overwrite",
        records=new_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="delete",
    )

    dt = DeltaTable(f"{temp_delta_path}/test_overwrite")
    df = dt.to_pandas()
    assert len(df) == 1
    assert df.iloc[0]["id"] == "3"


@pytest.mark.asyncio
async def test_write_silver_partitioning(
    delta_writer, temp_delta_path, sample_records, sample_schema
):
    """Test partitioning."""
    await delta_writer.write_silver(
        table_name="test_partition",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="delete",
        partition_cols=["val"],
    )

    base_path = Path(temp_delta_path) / "test_partition"
    assert (base_path / "val=A").exists()
    assert (base_path / "val=B").exists()
