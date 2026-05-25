"""Performance benchmarks for Delta Lake writes (Silver layer).

Measures Delta Lake write throughput with merge/append operations.
"""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.delta.resilience import (
    build_default_silver_merge_policy,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.benchmarks.conftest import calculate_payload_size_mb

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.performance,
    pytest.mark.serial,
    pytest.mark.timeout(120),
]


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
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
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


def _create_silver_writer(base_path: Path) -> SilverWriter:
    """Create an isolated Silver writer rooted at one benchmark round path."""
    return SilverWriter(
        base_path=base_path,
        logger=FakeLogger(),
        merge_resilience_policy=replace(
            build_default_silver_merge_policy(),
            # Benchmarks run inside pytest's outer timeout and should measure merge
            # throughput rather than trip the production-facing 45s safety window
            # on slower local Windows filesystems.
            execution_timeout_seconds=90.0,
        ),
    )


def _append_round_setup(
    *,
    delta_output_dir: Path,
    table_prefix: str,
    payload: list[dict[str, Any]],
) -> tuple[tuple[SilverWriter, str, list[dict[str, Any]], pa.Schema], dict[str, Any]]:
    """Prepare one isolated append round for pytest-benchmark pedantic mode."""
    round_root = delta_output_dir / f"{table_prefix}_{uuid4().hex[:8]}"
    round_root.mkdir(parents=True, exist_ok=True)
    writer = _create_silver_writer(round_root)
    return (
        writer,
        "benchmark_table",
        _prepare_records_for_delta(payload),
        _create_activity_schema(),
    ), {}


def _run_append_round(
    writer: SilverWriter,
    table_name: str,
    records: list[dict[str, Any]],
    schema: pa.Schema,
):
    """Execute one isolated Silver append write."""

    async def write_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    return asyncio.run(write_batch())


def _merge_round_setup(
    *,
    delta_output_dir: Path,
    payload: list[dict[str, Any]],
) -> tuple[tuple[SilverWriter, str, list[dict[str, Any]], pa.Schema], dict[str, Any]]:
    """Prepare one isolated merge round with a seeded Delta table."""
    round_root = delta_output_dir / f"benchmark_merge_{uuid4().hex[:8]}"
    round_root.mkdir(parents=True, exist_ok=True)
    writer = _create_silver_writer(round_root)
    records = _prepare_records_for_delta(payload)
    schema = _create_activity_schema()
    table_name = "benchmark_table"

    async def initial_write():
        return await writer.write_silver(
            table_name=table_name,
            records=records[:100],
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.APPEND,
        )

    asyncio.run(initial_write())
    return (writer, table_name, records, schema), {}


def _run_merge_round(
    writer: SilverWriter,
    table_name: str,
    records: list[dict[str, Any]],
    schema: pa.Schema,
):
    """Execute one isolated Silver merge write against a seeded table."""

    async def merge_batch():
        return await writer.write_silver(
            table_name=table_name,
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode=SilverWriteMode.MERGE,
        )

    return asyncio.run(merge_batch())


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_small(benchmark, small_payload, delta_output_dir):
    """Benchmark Delta append with small payload (100 records)."""
    result = benchmark.pedantic(
        _run_append_round,
        setup=lambda: _append_round_setup(
            delta_output_dir=delta_output_dir,
            table_prefix="benchmark_small",
            payload=small_payload,
        ),
        rounds=1,
        iterations=1,
    )

    assert result is not None

    size_mb = calculate_payload_size_mb(small_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(small_payload)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_medium(benchmark, medium_payload, delta_output_dir):
    """Benchmark Delta append with medium payload (1000 records)."""
    result = benchmark.pedantic(
        _run_append_round,
        setup=lambda: _append_round_setup(
            delta_output_dir=delta_output_dir,
            table_prefix="benchmark_medium",
            payload=medium_payload,
        ),
        rounds=1,
        iterations=1,
    )

    assert result is not None

    size_mb = calculate_payload_size_mb(medium_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(medium_payload)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta")
def test_delta_write_append_large(benchmark, large_payload, delta_output_dir):
    """Benchmark Delta append with large payload (5000 records)."""
    result = benchmark.pedantic(
        _run_append_round,
        setup=lambda: _append_round_setup(
            delta_output_dir=delta_output_dir,
            table_prefix="benchmark_large",
            payload=large_payload,
        ),
        rounds=1,
        iterations=1,
    )

    assert result is not None

    size_mb = calculate_payload_size_mb(large_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(large_payload)
    benchmark.extra_info["mode"] = "append"


@pytest.mark.benchmark(group="delta_merge")
def test_delta_write_merge_medium(benchmark, medium_payload, delta_output_dir):
    """Benchmark Delta merge with medium payload (1000 records).

    Merge is more expensive than append due to deduplication logic.
    """
    result = benchmark.pedantic(
        _run_merge_round,
        setup=lambda: _merge_round_setup(
            delta_output_dir=delta_output_dir,
            payload=medium_payload,
        ),
        rounds=1,
        iterations=1,
    )

    assert result is not None

    size_mb = calculate_payload_size_mb(medium_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(medium_payload)
    benchmark.extra_info["mode"] = "merge"
