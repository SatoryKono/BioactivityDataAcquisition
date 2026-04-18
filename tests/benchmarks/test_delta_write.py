"""Performance benchmarks for Delta Lake writes (Silver layer).

Measures Delta Lake write throughput with merge/append operations.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.benchmarks.conftest import calculate_payload_size_mb


class FakeLogger:
    """Minimal fake logger for benchmarks."""

    def info(self, _msg: str, **_kwargs: Any) -> None:
        return None

    def debug(self, _msg: str, **_kwargs: Any) -> None:
        return None

    def warning(self, _msg: str, **_kwargs: Any) -> None:
        return None

    def error(self, _msg: str, **_kwargs: Any) -> None:
        return None

    def bind(self, **_kwargs: Any) -> "FakeLogger":
        return self


def _create_activity_schema() -> pa.Schema:
    """Create a PyArrow schema for activity records."""
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("molecule_id", pa.string()),
            pa.field("assay_id", pa.string()),
            pa.field("target_id", pa.string()),
            pa.field("standard_value", pa.float64()),
            pa.field("standard_units", pa.string()),
            pa.field("pchembl_value", pa.float64()),
            pa.field("canonical_smiles", pa.string()),
            pa.field("_content_hash", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.timestamp("us")),
        ]
    )


def _prepare_records_for_delta(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add required metadata fields to records."""
    now = datetime.now(UTC)
    run_id = str(uuid4())
    prepared = []
    for record in records:
        rec = {
            "id": record.get("id", ""),
            "molecule_id": record.get("molecule_id", ""),
            "assay_id": record.get("assay_id", ""),
            "target_id": record.get("target_id", ""),
            "standard_value": record.get("standard_value"),
            "standard_units": record.get("standard_units", ""),
            "pchembl_value": record.get("pchembl_value"),
            "canonical_smiles": record.get("canonical_smiles", ""),
            "_content_hash": str(uuid4()),
            "_run_id": run_id,
            "_run_type": "benchmark",
            "_source_batch_id": "benchmark_batch_0001",
            "_ingestion_ts": now,
        }
        prepared.append(rec)
    return prepared


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_small(benchmark, small_payload, delta_output_dir):
    """Benchmark Delta append with small payload (100 records)."""
    logger = FakeLogger()
    writer = SilverWriter(base_path=delta_output_dir, logger=logger)

    schema = _create_activity_schema()
    records = _prepare_records_for_delta(small_payload)
    table_name = f"benchmark_small_{uuid4().hex[:8]}"

    async def write_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    assert result is not None

    size_mb = calculate_payload_size_mb(small_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(records)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_medium(benchmark, medium_payload, delta_output_dir):
    """Benchmark Delta append with medium payload (1000 records)."""
    logger = FakeLogger()
    writer = SilverWriter(base_path=delta_output_dir, logger=logger)

    schema = _create_activity_schema()
    records = _prepare_records_for_delta(medium_payload)
    table_name = f"benchmark_medium_{uuid4().hex[:8]}"

    async def write_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    assert result is not None

    size_mb = calculate_payload_size_mb(medium_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(records)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_large(benchmark, large_payload, delta_output_dir):
    """Benchmark Delta append with large payload (5000 records)."""
    logger = FakeLogger()
    writer = SilverWriter(base_path=delta_output_dir, logger=logger)

    schema = _create_activity_schema()
    records = _prepare_records_for_delta(large_payload)
    table_name = f"benchmark_large_{uuid4().hex[:8]}"

    async def write_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    assert result is not None

    size_mb = calculate_payload_size_mb(large_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(records)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta_merge")
def test_delta_write_merge_medium(benchmark, medium_payload, delta_output_dir):
    """Benchmark Delta merge with medium payload (1000 records).

    Merge is more expensive than append due to deduplication logic.
    """
    logger = FakeLogger()
    writer = SilverWriter(base_path=delta_output_dir, logger=logger)

    schema = _create_activity_schema()
    records = _prepare_records_for_delta(medium_payload)
    table_name = f"benchmark_merge_{uuid4().hex[:8]}"

    # First write to create the table
    async def initial_write():
        return await writer.write_silver(
            table_name=table_name,
            records=records[:100],
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    asyncio.run(initial_write())

    # Benchmark merge operation
    async def merge_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )

    result = benchmark(lambda: asyncio.run(merge_batch()))

    assert result is not None

    size_mb = calculate_payload_size_mb(medium_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(records)
    benchmark.extra_info["mode"] = "merge"
