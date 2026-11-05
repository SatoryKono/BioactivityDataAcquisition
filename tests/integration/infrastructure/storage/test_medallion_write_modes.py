"""Runtime evidence: Medallion write-mode matrix on real Delta writers."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from deltalake import DeltaTable
from pandera.pandas import Column, DataFrameSchema

from bioetl.domain.exceptions import SchemaEvolutionError
from bioetl.domain.ports import LoggerPort
from bioetl.domain.transformations import generate_content_hash
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.validation.pandera_validator import NoOpValidator
from tests.helpers.clock import fixed_test_clock

pytestmark = pytest.mark.integration

_SILVER_META_FIELDS: tuple[tuple[str, pa.DataType], ...] = (
    ("content_hash", pa.string()),
    ("_run_id", pa.string()),
    ("_run_type", pa.string()),
    ("_source_batch_id", pa.string()),
    ("_ingestion_ts", pa.string()),
)

_SILVER_META_VALUES: dict[str, str] = {
    "_run_id": "run-id",
    "_run_type": "incremental",
    "_source_batch_id": "batch-1",
    "_ingestion_ts": "2026-01-01T00:00:00+00:00",
}

_SCD2_CONFIG: dict[str, object] = {
    "valid_from_col": "valid_from",
    "valid_to_col": "valid_to",
    "is_current_col": "is_current",
    "identity_cols": ["id"],
    "update_cols": ["val"],
    "scd_type": 2,
    "business_key": "id",
}


class MockLogger(LoggerPort):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def bind(self, **kwargs: Any) -> LoggerPort:
        return self


def _silver_schema(*extra: tuple[str, pa.DataType]) -> pa.Schema:
    fields: list[tuple[str, pa.DataType]] = [("id", pa.string()), ("val", pa.string())]
    fields.extend(extra)
    fields.extend(_SILVER_META_FIELDS)
    return pa.schema(fields)


def _silver_record(record_id: str, val: str, **extra: str) -> dict[str, str]:
    payload = {"id": record_id, "val": val, **extra}
    return {
        "id": record_id,
        "val": val,
        **extra,
        "content_hash": str(generate_content_hash(payload, "test")),
        **_SILVER_META_VALUES,
    }


def _gold_record(record_id: str, val: str) -> dict[str, str]:
    payload = {"id": record_id, "val": val}
    return {
        "id": record_id,
        "val": val,
        "content_hash": str(generate_content_hash(payload, "test")),
    }


@pytest.fixture
def temp_delta_path(tmp_path: Path) -> str:
    path = tmp_path / "delta"
    path.mkdir()
    return str(path)


@pytest.fixture
def silver_writer(temp_delta_path: str) -> SilverWriter:
    logger = MockLogger()
    return SilverWriter(
        runtime_request=SilverWriterRuntimeServicesRequest(
            clock=fixed_test_clock(),
            logger=logger,
            silver_validator=NoOpValidator(),
        ),
        base_path=temp_delta_path,
        logger=logger,
    )


@pytest.fixture
def gold_schema() -> DataFrameSchema:
    return DataFrameSchema(
        {"id": Column(str), "val": Column(str), "content_hash": Column(str)},
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
        base_path=temp_delta_path, logger=logger, runtime_services=services
    )


@pytest.mark.asyncio
async def test_silver_writer_rejects_overwrite_mode(
    silver_writer: SilverWriter, temp_delta_path: str
) -> None:
    schema = pa.schema([("id", pa.string()), ("val", pa.string())])
    records = [{"id": "1", "val": "A"}]

    with pytest.raises(ValueError, match="Invalid Silver write mode"):
        await silver_writer.write_silver(
            table_name="test_silver",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="overwrite",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_gold_writer_rejects_invalid_mode(
    gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str
) -> None:
    records = [{"id": "1", "val": "A", "content_hash": "hash"}]
    with pytest.raises(ValueError, match="Invalid Gold write mode"):
        await gold_writer.write_gold(
            table_name="test_gold",
            records=records,
            schema=gold_schema,
            primary_keys=["id"],
            mode="invalid_mode",
        )


@pytest.mark.asyncio
async def test_silver_writer_allows_append_and_merge(
    silver_writer: SilverWriter, temp_delta_path: str
) -> None:
    schema = _silver_schema()
    records = [_silver_record("1", "A")]

    await silver_writer.write_silver(
        table_name="test_silver",
        records=records,
        primary_keys=["id"],
        schema=schema,
        mode="append",
    )
    await silver_writer.write_silver(
        table_name="test_silver",
        records=[_silver_record("1", "B")],
        primary_keys=["id"],
        schema=schema,
        mode="merge",
    )

    df = DeltaTable(f"{temp_delta_path}/test_silver").to_pandas()
    assert len(df) == 1
    assert df["val"].iloc[0] == "B"


@pytest.mark.asyncio
async def test_gold_writer_allows_append_and_overwrite(
    gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str
) -> None:
    table_path = f"{temp_delta_path}/test_gold_write_modes"
    await gold_writer.write_gold(
        table_name="test_gold_write_modes",
        records=[_gold_record("1", "A")],
        primary_keys=["id"],
        schema=gold_schema,
        mode="append",
    )
    appended = DeltaTable(table_path).to_pandas()
    assert len(appended) == 1
    assert appended["val"].iloc[0] == "A"

    await gold_writer.write_gold(
        table_name="test_gold_write_modes",
        records=[_gold_record("1", "B"), _gold_record("2", "C")],
        primary_keys=["id"],
        schema=gold_schema,
        mode="overwrite",
    )

    df = DeltaTable(table_path).to_pandas()
    assert len(df) == 2
    assert set(df["id"]) == {"1", "2"}
    assert df[df["id"] == "1"]["val"].iloc[0] == "B"
    assert df[df["id"] == "2"]["val"].iloc[0] == "C"


@pytest.mark.asyncio
async def test_silver_writer_schema_drift(
    silver_writer: SilverWriter, temp_delta_path: str
) -> None:
    await silver_writer.write_silver(
        table_name="test_silver_drift",
        records=[_silver_record("1", "A")],
        primary_keys=["id"],
        schema=_silver_schema(),
        mode="append",
    )

    with pytest.raises(SchemaEvolutionError):
        await silver_writer.write_silver(
            table_name="test_silver_drift",
            records=[_silver_record("2", "B", new_field="C")],
            primary_keys=["id"],
            schema=_silver_schema(("new_field", pa.string())),
            mode="append",
        )


@pytest.mark.asyncio
async def test_silver_writer_schema_drift_evolve(
    silver_writer: SilverWriter, temp_delta_path: str
) -> None:
    await silver_writer.write_silver(
        table_name="test_silver_drift_evolve",
        records=[_silver_record("1", "A")],
        primary_keys=["id"],
        schema=_silver_schema(),
        mode="append",
    )
    await silver_writer.write_silver(
        table_name="test_silver_drift_evolve",
        records=[_silver_record("2", "B", new_field="C")],
        primary_keys=["id"],
        schema=_silver_schema(("new_field", pa.string())),
        mode="append",
        on_schema_mismatch="evolve",
    )

    df = DeltaTable(f"{temp_delta_path}/test_silver_drift_evolve").to_pandas()
    assert len(df) == 2
    assert "new_field" in df.columns
    assert set(df["id"]) == {"1", "2"}


@pytest.mark.asyncio
async def test_gold_writer_scd2_with_ts(
    gold_writer: GoldWriter, gold_schema: DataFrameSchema, temp_delta_path: str
) -> None:
    await gold_writer.write_gold(
        table_name="test_gold_scd2_ts",
        records=[_gold_record("1", "A")],
        primary_keys=["id"],
        schema=gold_schema,
        mode="scd2",
        scd_config=_SCD2_CONFIG,
        ingestion_ts=datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
    )
    await gold_writer.write_gold(
        table_name="test_gold_scd2_ts",
        records=[_gold_record("1", "B")],
        primary_keys=["id"],
        schema=gold_schema,
        mode="scd2",
        scd_config=_SCD2_CONFIG,
        ingestion_ts=datetime.datetime(2026, 1, 2, 0, 0, 0, tzinfo=datetime.UTC),
    )

    df = DeltaTable(f"{temp_delta_path}/test_gold_scd2_ts").to_pandas()
    assert len(df) == 2
    assert set(df["id"]) == {"1"}

    current_df = df[df["is_current"]]
    assert len(current_df) == 1
    assert current_df["val"].iloc[0] == "B"

    historical_df = df[~df["is_current"]]
    assert len(historical_df) == 1
    assert historical_df["val"].iloc[0] == "A"
