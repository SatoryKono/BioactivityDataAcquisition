import pyarrow as pa
import pytest
from pathlib import Path
import datetime
from deltalake import DeltaTable
from pandera.pandas import DataFrameSchema, Column

from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import SilverWriterRuntimeServicesRequest
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.gold.runtime_helpers import build_gold_writer_runtime_services
from tests.helpers.clock import fixed_test_clock
from bioetl.domain.ports import LoggerPort
from bioetl.domain.transformations import generate_content_hash
from typing import Any

class MockLogger(LoggerPort):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: pass
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: pass
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: pass
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: pass
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None: pass
    def bind(self, **kwargs: Any) -> LoggerPort: return self


@pytest.fixture
def temp_delta_path(tmp_path: Path) -> str:
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)

@pytest.fixture
def silver_writer(temp_delta_path: str) -> SilverWriter:
    logger = MockLogger()
    return SilverWriter(
        runtime_request=SilverWriterRuntimeServicesRequest(clock=fixed_test_clock(), logger=logger),
        base_path=temp_delta_path,
        logger=logger,
    )

@pytest.fixture
def gold_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {
            "id": Column(str),
            "val": Column(str),
            "content_hash": Column(str)
        },
        strict=True,
    )

@pytest.fixture
def gold_writer(temp_delta_path: str) -> GoldWriter:
    logger = MockLogger()
    services = build_gold_writer_runtime_services(
        csv_exporter=None,
        tracing=None,
        metrics=None,
        audit=None,
        metadata_writer=None,
        metadata_coordinator=None,
        lineage_store=None,
    )
    return GoldWriter(
        base_path=temp_delta_path,
        logger=logger,
        runtime_services=services
    )

@pytest.mark.asyncio
async def test_silver_writer_rejects_overwrite_mode(silver_writer: SilverWriter, temp_delta_path: str) -> None:
    schema = pa.schema([("id", pa.string()), ("val", pa.string())])
    records = [{"id": "1", "val": "A"}]

    with pytest.raises(ValueError, match="Invalid Silver write mode"):
        await silver_writer.write_silver(
            table_name="test_silver",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="overwrite"  # type: ignore[arg-type]
        )

@pytest.mark.asyncio
async def test_gold_writer_rejects_invalid_mode(gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str) -> None:
    records = [{"id": "1", "val": "A", "content_hash": "hash"}]
    with pytest.raises(ValueError, match="Invalid Gold write mode"):
        await gold_writer.write_gold(
            table_name="test_gold",
            records=records,
            schema=gold_schema,
            primary_keys=["id"],
            mode="invalid_mode"
        )


@pytest.mark.asyncio
async def test_silver_writer_allows_append_and_merge(silver_writer: SilverWriter, temp_delta_path: str) -> None:
    schema = pa.schema([
            ("id", pa.string()),
            ("val", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ])
    def _record(record_id: str, val: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val}
        return {
            "id": record_id,
            "val": val,
            "content_hash": str(generate_content_hash(payload, "test")),
            "_run_id": "run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }
    records = [_record("1", "A")]

    # Write append
    await silver_writer.write_silver(
        table_name="test_silver",
        records=records,
        primary_keys=["id"],
        schema=schema,
        mode="append"
    )

    records_update = [_record("1", "B")]
    # Write merge
    await silver_writer.write_silver(
        table_name="test_silver",
        records=records_update,
        primary_keys=["id"],
        schema=schema,
        mode="merge"
    )

    df = DeltaTable(f"{temp_delta_path}/test_silver").to_pandas()
    assert len(df) == 1
    # Check that merge updated the value
    assert df["val"].iloc[0] == "B"


@pytest.mark.asyncio
async def test_gold_writer_allows_append_and_overwrite(gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str) -> None:
    def _record(record_id: str, val: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val}
        return {
            "id": record_id,
            "val": val,
            "content_hash": str(generate_content_hash(payload, "test")),
        }

    records = [_record("1", "A")]

    # Write append
    await gold_writer.write_gold(
        table_name="test_gold_write_modes",
        records=records,
        primary_keys=["id"],
        schema=gold_schema,
        mode="append"
    )

    records_update = [_record("1", "B"), _record("2", "C")]
    # Write overwrite
    await gold_writer.write_gold(
        table_name="test_gold_write_modes",
        records=records_update,
        primary_keys=["id"],
        schema=gold_schema,
        mode="overwrite"
    )

    df = DeltaTable(f"{temp_delta_path}/test_gold_write_modes").to_pandas()
    assert len(df) == 2
    assert set(df["id"]) == {"1", "2"}
    assert df[df["id"] == "1"]["val"].iloc[0] == "B"
    assert df[df["id"] == "2"]["val"].iloc[0] == "C"

@pytest.mark.asyncio
async def test_silver_writer_schema_drift(silver_writer: SilverWriter, temp_delta_path: str) -> None:
    schema = pa.schema([
            ("id", pa.string()),
            ("val", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ])
    def _record(record_id: str, val: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val}
        return {
            "id": record_id,
            "val": val,
            "content_hash": str(generate_content_hash(payload, "test")),
            "_run_id": "run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }
    records = [_record("1", "A")]

    # Write append
    await silver_writer.write_silver(
        table_name="test_silver_drift",
        records=records,
        primary_keys=["id"],
        schema=schema,
        mode="append"
    )

    schema_v2 = pa.schema([
            ("id", pa.string()),
            ("val", pa.string()),
            ("new_field", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ])

    def _record_v2(record_id: str, val: str, new_field: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val, "new_field": new_field}
        return {
            "id": record_id,
            "val": val,
            "new_field": new_field,
            "content_hash": str(generate_content_hash(payload, "test")),
            "_run_id": "run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }

    records_v2 = [_record_v2("2", "B", "C")]

    with pytest.raises(Exception):
        await silver_writer.write_silver(
            table_name="test_silver_drift",
            records=records_v2,
            primary_keys=["id"],
            schema=schema_v2,
            mode="append"
        )

@pytest.mark.asyncio
async def test_silver_writer_schema_drift_evolve(silver_writer: SilverWriter, temp_delta_path: str) -> None:
    schema = pa.schema([
            ("id", pa.string()),
            ("val", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ])
    def _record(record_id: str, val: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val}
        return {
            "id": record_id,
            "val": val,
            "content_hash": str(generate_content_hash(payload, "test")),
            "_run_id": "run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }
    records = [_record("1", "A")]

    # Write append
    await silver_writer.write_silver(
        table_name="test_silver_drift_evolve",
        records=records,
        primary_keys=["id"],
        schema=schema,
        mode="append"
    )

    schema_v2 = pa.schema([
            ("id", pa.string()),
            ("val", pa.string()),
            ("new_field", pa.string()),
            ("content_hash", pa.string()),
            ("_run_id", pa.string()),
            ("_run_type", pa.string()),
            ("_source_batch_id", pa.string()),
            ("_ingestion_ts", pa.string()),
        ])

    def _record_v2(record_id: str, val: str, new_field: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val, "new_field": new_field}
        return {
            "id": record_id,
            "val": val,
            "new_field": new_field,
            "content_hash": str(generate_content_hash(payload, "test")),
            "_run_id": "run-id",
            "_run_type": "incremental",
            "_source_batch_id": "batch-1",
            "_ingestion_ts": "2026-01-01T00:00:00+00:00",
        }

    records_v2 = [_record_v2("2", "B", "C")]

    await silver_writer.write_silver(
        table_name="test_silver_drift_evolve",
        records=records_v2,
        primary_keys=["id"],
        schema=schema_v2,
        mode="append",
        on_schema_mismatch="evolve"
    )

    df = DeltaTable(f"{temp_delta_path}/test_silver_drift_evolve").to_pandas()
    assert len(df) == 2
    assert "new_field" in df.columns
    assert set(df["id"]) == {"1", "2"}


@pytest.mark.asyncio
async def test_gold_writer_scd2_with_ts(gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str) -> None:
    def _record(record_id: str, val: str) -> dict[str, str]:
        payload = {"id": record_id, "val": val}
        return {
            "id": record_id,
            "val": val,
            "content_hash": str(generate_content_hash(payload, "test")),
        }

    records = [_record("1", "A")]

    scd_config = {
        "valid_from_col": "valid_from",
        "valid_to_col": "valid_to",
        "is_current_col": "is_current",
        "identity_cols": ["id"],
        "update_cols": ["val"],
        "scd_type": 2,
        "business_key": "id"
    }

    # Write scd2 initial
    await gold_writer.write_gold(
        table_name="test_gold_scd2_ts",
        records=records,
        primary_keys=["id"],
        schema=gold_schema,
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
    )

    records_update = [_record("1", "B")]
    # Write scd2 update
    await gold_writer.write_gold(
        table_name="test_gold_scd2_ts",
        records=records_update,
        primary_keys=["id"],
        schema=gold_schema,
        mode="scd2",
        scd_config=scd_config,
        ingestion_ts=datetime.datetime(2026, 1, 2, 0, 0, 0, tzinfo=datetime.UTC)
    )

    df = DeltaTable(f"{temp_delta_path}/test_gold_scd2_ts").to_pandas()
    # 1 record created initially, and 1 record added as new version
    assert len(df) == 2
    assert set(df["id"]) == {"1"}

    current_df = df[df["is_current"]]
    assert len(current_df) == 1
    assert current_df["val"].iloc[0] == "B"

    historical_df = df[~df["is_current"]]
    assert len(historical_df) == 1
    assert historical_df["val"].iloc[0] == "A"
