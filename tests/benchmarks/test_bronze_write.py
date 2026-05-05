"""Performance benchmarks for Bronze layer writes.

Measures JSONL + zstd compression throughput.
"""

import asyncio
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from tests.benchmarks.conftest import calculate_payload_size_mb


def _records_to_bytes_iterator(records: list[dict[str, Any]]) -> Iterator[bytes]:
    """Convert records to bytes iterator for BronzeWriter."""
    for record in records:
        yield (json.dumps(record) + "\n").encode("utf-8")


class FakeMetrics:
    """Minimal fake metrics for benchmarks."""

    def observe_histogram(self, *args: Any, **kwargs: Any) -> None:
        # Intentionally left blank: metrics are not collected in benchmarks.
        pass

    def increment_counter(self, *args: Any, **kwargs: Any) -> None:
        # Intentionally left blank: metrics are not collected in benchmarks.
        return None


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


@pytest.mark.benchmark(group="bronze")
def test_bronze_write_small(benchmark, small_payload, bronze_output_dir):
    """Benchmark Bronze write with small payload (100 records)."""
    from bioetl.domain.types import BatchID, RunID, RunType
    from bioetl.infrastructure.storage.bronze_write_result_helpers import (
        is_bronze_write_result_persisted,
    )
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    logger = FakeLogger()
    metrics = FakeMetrics()
    writer = BronzeWriter(base_path=bronze_output_dir, logger=logger, metrics=metrics)

    run_id = RunID(uuid4())
    batch_id = BatchID(uuid4())
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    async def write_batch():
        records_iter = _records_to_bytes_iterator(small_payload)
        return await writer.write_bronze(
            records=records_iter,
            provider="benchmark",
            entity="small",
            date=now,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=now,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    # Verify output exists
    assert result is not None
    assert is_bronze_write_result_persisted(result)

    # Report payload size
    size_mb = calculate_payload_size_mb(small_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(small_payload)


@pytest.mark.benchmark(group="bronze")
def test_bronze_write_medium(benchmark, medium_payload, bronze_output_dir):
    """Benchmark Bronze write with medium payload (1000 records)."""
    from bioetl.domain.types import BatchID, RunID, RunType
    from bioetl.infrastructure.storage.bronze_write_result_helpers import (
        is_bronze_write_result_persisted,
    )
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    logger = FakeLogger()
    metrics = FakeMetrics()
    writer = BronzeWriter(base_path=bronze_output_dir, logger=logger, metrics=metrics)

    run_id = RunID(uuid4())
    batch_id = BatchID(uuid4())
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    async def write_batch():
        records_iter = _records_to_bytes_iterator(medium_payload)
        return await writer.write_bronze(
            records=records_iter,
            provider="benchmark",
            entity="medium",
            date=now,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=now,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    assert result is not None
    assert is_bronze_write_result_persisted(result)

    size_mb = calculate_payload_size_mb(medium_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(medium_payload)


@pytest.mark.benchmark(group="bronze")
def test_bronze_write_large(benchmark, large_payload, bronze_output_dir):
    """Benchmark Bronze write with large payload (5000 records)."""
    from bioetl.domain.types import BatchID, RunID, RunType
    from bioetl.infrastructure.storage.bronze_write_result_helpers import (
        is_bronze_write_result_persisted,
    )
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    logger = FakeLogger()
    metrics = FakeMetrics()
    writer = BronzeWriter(base_path=bronze_output_dir, logger=logger, metrics=metrics)

    run_id = RunID(uuid4())
    batch_id = BatchID(uuid4())
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    async def write_batch():
        records_iter = _records_to_bytes_iterator(large_payload)
        return await writer.write_bronze(
            records=records_iter,
            provider="benchmark",
            entity="large",
            date=now,
            batch_id=batch_id,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            ingestion_ts=now,
        )

    result = benchmark(lambda: asyncio.run(write_batch()))

    assert result is not None
    assert is_bronze_write_result_persisted(result)

    size_mb = calculate_payload_size_mb(large_payload)
    benchmark.extra_info["payload_size_mb"] = round(size_mb, 3)
    benchmark.extra_info["records"] = len(large_payload)
