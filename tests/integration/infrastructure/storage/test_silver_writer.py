"""Integration tests for SilverWriter."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.domain.transformations import generate_content_hash
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = pytest.mark.integration


class RecordingLogger:
    """Minimal logger that records structured events for storage tests."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def bind(self, **_kwargs: object) -> RecordingLogger:
        return self

    def info(self, event: str, **kwargs: object) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: object) -> None:
        self.events.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: object) -> None:
        self.events.append(("error", event, kwargs))

    def debug(self, event: str, **kwargs: object) -> None:
        self.events.append(("debug", event, kwargs))


def _create_content_hash_schema() -> pa.Schema:
    """Create the common Silver schema with content hash metadata."""
    return pa.schema(
        [
            ("id", pa.string()),
            ("val", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ]
    )


def _create_dual_write_writer(
    *,
    temp_delta_path: str,
    noop_logger: object,
    logger: object,
    active_version: str,
    read_order: tuple[str, ...],
    write_versions: tuple[str, ...],
    affects_hash: bool,
) -> SilverWriter:
    """Build a SilverWriter wired for contract dual-write tests."""
    return SilverWriter(
        base_path=temp_delta_path,
        logger=noop_logger,
        runtime_services=build_silver_writer_runtime_services(
            SilverWriterRuntimeServicesRequest(
                csv_exporter=None,
                tracing=None,
                write_policy=None,
                metrics=None,
                audit=None,
                logger=logger,
                silver_validator=None,
                metadata_writer=None,
                metadata_coordinator=None,
                lineage_store=None,
                dq_calculator=None,
                merge_resilience_policy=None,
                base_path=temp_delta_path,
                contract_rollout_policy=ContractRolloutPolicy(
                    contract_ref="chembl.activity",
                    active_version=active_version,
                    mode="dual_read_write",
                    read_order=read_order,
                    write_versions=write_versions,
                    affects_hash=affects_hash,
                ),
            )
        ),
    )


def _create_dual_write_record(
    *,
    content_hash: str,
    content_hashes_by_version: dict[str, str] | None = None,
) -> dict[str, object]:
    """Create a minimal logical Silver record for dual-write tests."""
    record: dict[str, object] = {
        "id": "1",
        "val": "A",
        "content_hash": content_hash,
        "_run_id": "run1",
        "_run_type": "incremental",
        "_source_batch_id": "batch1",
        "_ingestion_ts": "2023-01-01T00:00:00",
    }
    if content_hashes_by_version is not None:
        record["_content_hashes_by_version"] = content_hashes_by_version
    return record


def _create_runtime_record(
    *,
    record_id: str,
    val: str,
    run_id: str = "run1",
    source_batch_id: str = "batch1",
    ingestion_ts: str = "2023-01-01T00:00:00",
    with_content_hash: bool = False,
) -> dict[str, str]:
    """Create a standard Silver test record with optional content hash."""
    record = {
        "id": record_id,
        "val": val,
        "_run_id": run_id,
        "_run_type": "incremental",
        "_source_batch_id": source_batch_id,
        "_ingestion_ts": ingestion_ts,
    }
    if with_content_hash:
        record["content_hash"] = str(
            generate_content_hash({"id": record_id, "val": val}, "test")
        )
    return record


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
        _create_runtime_record(record_id="1", val="A"),
        _create_runtime_record(record_id="2", val="B"),
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


@pytest.fixture
def sample_schema_with_content_hash():
    return _create_content_hash_schema()


@pytest.mark.asyncio
@pytest.mark.timeout(120)
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
        _create_runtime_record(
            record_id="1",
            val="A_updated",
            run_id="run2",
            source_batch_id="batch2",
            ingestion_ts="2023-01-02T00:00:00",
        ),
        _create_runtime_record(
            record_id="3",
            val="C",
            run_id="run2",
            source_batch_id="batch2",
            ingestion_ts="2023-01-02T00:00:00",
        ),
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
@pytest.mark.timeout(120)
async def test_write_silver_merge_is_idempotent_for_identical_input(
    silver_writer, temp_delta_path, sample_schema_with_content_hash
):
    """Merge with identical input should preserve row count and identity set."""
    records = [
        _create_runtime_record(record_id="1", val="A", with_content_hash=True),
        _create_runtime_record(record_id="2", val="B", with_content_hash=True),
    ]

    await silver_writer.write_silver(
        table_name="test_merge_idempotent",
        records=records,
        primary_keys=["id"],
        schema=sample_schema_with_content_hash,
    )

    dt = DeltaTable(f"{temp_delta_path}/test_merge_idempotent")
    first_df = dt.to_pandas().sort_values("id").reset_index(drop=True)
    first_rows = first_df.to_dict(orient="records")
    first_identity = {(row["id"], row["content_hash"]) for row in first_rows}

    await silver_writer.write_silver(
        table_name="test_merge_idempotent",
        records=records,
        primary_keys=["id"],
        schema=sample_schema_with_content_hash,
    )

    dt = DeltaTable(f"{temp_delta_path}/test_merge_idempotent")
    second_df = dt.to_pandas().sort_values("id").reset_index(drop=True)
    second_rows = second_df.to_dict(orient="records")
    second_identity = {(row["id"], row["content_hash"]) for row in second_rows}

    assert len(second_df) == len(first_df)
    assert second_rows == first_rows
    assert second_identity == first_identity


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_write_silver_merge_ignores_metadata_only_rerun(
    silver_writer, temp_delta_path, sample_schema_with_content_hash
):
    """Metadata-only reruns should not rewrite existing Silver rows."""
    first_records = [
        _create_runtime_record(record_id="1", val="A", with_content_hash=True)
    ]
    rerun_records = [
        _create_runtime_record(
            record_id="1",
            val="A",
            run_id="run2",
            source_batch_id="batch2",
            ingestion_ts="2023-01-02T00:00:00",
            with_content_hash=True,
        )
    ]

    await silver_writer.write_silver(
        table_name="test_merge_metadata_only_rerun",
        records=first_records,
        primary_keys=["id"],
        schema=sample_schema_with_content_hash,
    )

    dt = DeltaTable(f"{temp_delta_path}/test_merge_metadata_only_rerun")
    first_rows = (
        dt.to_pandas()
        .sort_values("id")
        .reset_index(drop=True)
        .to_dict(orient="records")
    )

    await silver_writer.write_silver(
        table_name="test_merge_metadata_only_rerun",
        records=rerun_records,
        primary_keys=["id"],
        schema=sample_schema_with_content_hash,
    )

    dt = DeltaTable(f"{temp_delta_path}/test_merge_metadata_only_rerun")
    second_rows = (
        dt.to_pandas()
        .sort_values("id")
        .reset_index(drop=True)
        .to_dict(orient="records")
    )

    assert second_rows == first_rows


@pytest.mark.asyncio
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
async def test_write_silver_persisted_rows_strip_runtime_occurrence_fields(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Persisted Silver rows should exclude run-scoped runtime provenance fields."""
    await silver_writer.write_silver(
        table_name="test_persisted_contract",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
        mode="append",
    )

    dt = DeltaTable(f"{temp_delta_path}/test_persisted_contract")
    table = dt.to_pyarrow_table()

    assert table.column_names == ["id", "val"]


@pytest.mark.asyncio
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
async def test_read_silver_returns_records(
    silver_writer, temp_delta_path, sample_records, sample_schema
):
    """Test read_silver returns records from existing table."""
    await silver_writer.write_silver(
        table_name="test_read",
        records=sample_records,
        primary_keys=["id"],
        schema=sample_schema,
    )

    records = await silver_writer.read_silver("test_read")

    assert len(records) == 2
    assert any(r["id"] == "1" and r["val"] == "A" for r in records)
    assert any(r["id"] == "2" and r["val"] == "B" for r in records)


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_write_silver_dual_write_routes_to_all_versioned_tables(
    temp_delta_path: str,
    noop_logger,
) -> None:
    """Dual-write should persist the same logical batch to all versioned tables."""
    writer = _create_dual_write_writer(
        temp_delta_path=temp_delta_path,
        noop_logger=noop_logger,
        logger=noop_logger,
        active_version="2.0.0",
        read_order=("2.0.0", "1.0.0"),
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=True,
    )
    schema = _create_content_hash_schema()
    records = [
        _create_dual_write_record(
            content_hash="active-hash",
            content_hashes_by_version={
                "1.0.0": "legacy-hash",
                "2.0.0": "active-hash",
            },
        )
    ]

    result = await writer.write_silver(
        table_name="chembl.activity",
        records=records,
        primary_keys=["id"],
        schema=schema,
        mode="append",
    )

    old_table = DeltaTable(f"{temp_delta_path}/chembl/activity__v1_0_0")
    new_table = DeltaTable(f"{temp_delta_path}/chembl/activity__v2_0_0")

    assert result is not None
    assert result.table_name == "chembl.activity__v2_0_0"
    assert old_table.to_pandas()["content_hash"].iloc[0] == "legacy-hash"
    assert new_table.to_pandas()["content_hash"].iloc[0] == "active-hash"


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_write_silver_dual_write_accepts_runtime_services_without_logger(
    temp_delta_path: str,
    noop_logger,
) -> None:
    """Runtime services should fall back to a no-op logger for direct test wiring."""
    writer = _create_dual_write_writer(
        temp_delta_path=temp_delta_path,
        noop_logger=noop_logger,
        logger=None,
        active_version="1.0.0",
        read_order=("1.0.0", "2.0.0"),
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=False,
    )
    schema = _create_content_hash_schema()

    result = await writer.write_silver(
        table_name="chembl.activity",
        records=[_create_dual_write_record(content_hash="stable-hash")],
        primary_keys=["id"],
        schema=schema,
        mode="append",
    )

    old_table = DeltaTable(f"{temp_delta_path}/chembl/activity__v1_0_0")
    new_table = DeltaTable(f"{temp_delta_path}/chembl/activity__v2_0_0")

    assert result is not None
    assert old_table.to_pandas()["content_hash"].iloc[0] == "stable-hash"
    assert new_table.to_pandas()["content_hash"].iloc[0] == "stable-hash"


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_write_silver_dual_write_fails_logical_write_when_any_target_fails(
    temp_delta_path: str,
    noop_logger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any failed physical target should fail the logical Silver dual-write."""
    writer = _create_dual_write_writer(
        temp_delta_path=temp_delta_path,
        noop_logger=noop_logger,
        logger=noop_logger,
        active_version="2.0.0",
        read_order=("2.0.0", "1.0.0"),
        write_versions=("1.0.0", "2.0.0"),
        affects_hash=True,
    )
    schema = _create_content_hash_schema()
    records = [
        _create_dual_write_record(
            content_hash="active-hash",
            content_hashes_by_version={
                "1.0.0": "legacy-hash",
                "2.0.0": "active-hash",
            },
        )
    ]
    observed_targets: list[str] = []

    async def _failing_write_single_target(**kwargs: object) -> SimpleNamespace:
        await asyncio.sleep(0)
        table_name = str(kwargs["table_name"])
        observed_targets.append(table_name)
        if table_name.endswith("__v2_0_0"):
            raise RuntimeError("simulated target failure")
        return SimpleNamespace(table_name=table_name)

    monkeypatch.setattr(writer, "_write_single_target", _failing_write_single_target)

    with pytest.raises(RuntimeError, match="simulated target failure"):
        await writer.write_silver(
            table_name="chembl.activity",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="append",
        )

    assert observed_targets == [
        "chembl.activity__v1_0_0",
        "chembl.activity__v2_0_0",
    ]


@pytest.mark.asyncio
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
async def test_read_silver_table_not_found(silver_writer):
    """Test read_silver raises FileNotFoundError for missing table."""
    with pytest.raises(FileNotFoundError, match="Table not found"):
        await silver_writer.read_silver("nonexistent_table")


@pytest.mark.asyncio
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
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
@pytest.mark.timeout(120)
async def test_write_silver_merged_strips_runtime_occurrence_fields(
    silver_writer, temp_delta_path
):
    """Merged Silver overwrite should not persist run-scoped provenance columns."""
    await silver_writer.write_silver_merged(
        table_name="test_merged_runtime_contract",
        records=[
            {
                "id": "1",
                "val": "A",
                "_run_id": "run-1",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2024-01-01T00:00:00Z",
            }
        ],
        primary_keys=["id"],
    )

    dt = DeltaTable(f"{temp_delta_path}/test_merged_runtime_contract")
    table = dt.to_pyarrow_table()

    assert table.column_names == ["id", "val"]


@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_write_silver_merged_empty_records(temp_delta_path: str):
    """Test write_silver_merged handles empty records gracefully."""
    logger = RecordingLogger()
    silver_writer = SilverWriter(base_path=temp_delta_path, logger=logger)

    # Should not raise, just log warning
    await silver_writer.write_silver_merged(
        table_name="test_empty",
        records=[],
    )

    assert (
        "warning",
        "No records to write for merged Silver",
        {"table_name": "test_empty"},
    ) in logger.events
    assert not (Path(temp_delta_path) / "test_empty").exists()
