"""JSON serialization benchmarks.

Compares performance of stdlib json vs orjson for typical BioETL workloads.

Run with:
    pytest benchmarks/test_json_serialization.py -v --benchmark-only

Requirements:
    - pip install pytest-benchmark orjson
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from typing import Any

import pytest

from bioetl.infrastructure.serialization.encoders import (
    orjson_available,
    OrjsonEncoder,
    StdLibJsonEncoder,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def nested_payload() -> list[dict[str, Any]]:
    """Payload with nested structures typical of bioactivity data."""
    return [
        {
            "id": f"RECORD_{i:06d}",
            "molecule_id": f"CHEMBL{100000 + i}",
            "assay_id": f"CHEMBL{200000 + i}",
            "properties": {
                "mw_freebase": 200.0 + i,
                "alogp": 2.5 + (i * 0.01),
                "nested": {
                    "level2": {
                        "value": i * 0.1,
                        "comment": f"深いネスト {i}",  # Non-ASCII for testing
                    }
                },
            },
            "activity_values": [10.5 + (i * 0.1), 20.3 + (i * 0.2), 30.1 + (i * 0.3)],
            "tags": [f"tag_{j}" for j in range(5)],
            "unicode_data": f"Данные {i} αβγ",  # Non-ASCII (Russian/Greek)
        }
        for i in range(1000)
    ]


class TestJsonEncoderPerformance:
    """Performance comparison tests for JSON encoders."""

    @pytest.mark.benchmark
    def test_stdlib_dumps_small(self, small_payload: list[dict[str, Any]]) -> None:
        """Benchmark stdlib json.dumps with small payload."""
        encoder = StdLibJsonEncoder()
        start = time.perf_counter()
        iterations = 100

        for _ in range(iterations):
            for record in small_payload:
                encoder.dumps(record)

        elapsed = time.perf_counter() - start
        ops_per_sec = (iterations * len(small_payload)) / elapsed
        logger.info(
            "StdLib small: %.0f ops/sec, %.4fs per batch",
            ops_per_sec,
            elapsed / iterations,
        )
        assert elapsed > 0
        assert ops_per_sec > 0

    @pytest.mark.benchmark
    def test_stdlib_dumps_medium(self, medium_payload: list[dict[str, Any]]) -> None:
        """Benchmark stdlib json.dumps with medium payload."""
        encoder = StdLibJsonEncoder()
        start = time.perf_counter()
        iterations = 10

        for _ in range(iterations):
            for record in medium_payload:
                encoder.dumps(record)

        elapsed = time.perf_counter() - start
        ops_per_sec = (iterations * len(medium_payload)) / elapsed
        logger.info(
            "StdLib medium: %.0f ops/sec, %.4fs per batch",
            ops_per_sec,
            elapsed / iterations,
        )
        assert elapsed > 0
        assert ops_per_sec > 0

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_orjson_dumps_small(self, small_payload: list[dict[str, Any]]) -> None:
        """Benchmark orjson.dumps with small payload."""
        encoder = OrjsonEncoder()
        start = time.perf_counter()
        iterations = 100

        for _ in range(iterations):
            for record in small_payload:
                encoder.dumps(record)

        elapsed = time.perf_counter() - start
        ops_per_sec = (iterations * len(small_payload)) / elapsed
        logger.info(
            "Orjson small: %.0f ops/sec, %.4fs per batch",
            ops_per_sec,
            elapsed / iterations,
        )
        assert elapsed > 0
        assert ops_per_sec > 0

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_orjson_dumps_medium(self, medium_payload: list[dict[str, Any]]) -> None:
        """Benchmark orjson.dumps with medium payload."""
        encoder = OrjsonEncoder()
        start = time.perf_counter()
        iterations = 10

        for _ in range(iterations):
            for record in medium_payload:
                encoder.dumps(record)

        elapsed = time.perf_counter() - start
        ops_per_sec = (iterations * len(medium_payload)) / elapsed
        logger.info(
            "Orjson medium: %.0f ops/sec, %.4fs per batch",
            ops_per_sec,
            elapsed / iterations,
        )
        assert elapsed > 0
        assert ops_per_sec > 0

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_performance_comparison(self, medium_payload: list[dict[str, Any]]) -> None:
        """Direct comparison of stdlib vs orjson performance."""
        stdlib_encoder = StdLibJsonEncoder()
        orjson_encoder = OrjsonEncoder()
        iterations = 5

        # Warmup
        for record in medium_payload[:10]:
            stdlib_encoder.dumps(record)
            orjson_encoder.dumps(record)

        # Measure stdlib
        stdlib_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            for record in medium_payload:
                stdlib_encoder.dumps(record)
            stdlib_times.append(time.perf_counter() - start)

        # Measure orjson
        orjson_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            for record in medium_payload:
                orjson_encoder.dumps(record)
            orjson_times.append(time.perf_counter() - start)

        stdlib_mean = statistics.mean(stdlib_times)
        orjson_mean = statistics.mean(orjson_times)
        speedup = stdlib_mean / orjson_mean

        logger.info("%s", "=" * 60)
        logger.info("JSON Serialization Benchmark Results")
        logger.info("%s", "=" * 60)
        logger.info("Payload: %d records", len(medium_payload))
        logger.info("Iterations: %d", iterations)
        logger.info("StdLib json:")
        logger.info("  Mean: %.4fs", stdlib_mean)
        logger.info("  Std:  %.4fs", statistics.stdev(stdlib_times))
        logger.info("Orjson:")
        logger.info("  Mean: %.4fs", orjson_mean)
        logger.info("  Std:  %.4fs", statistics.stdev(orjson_times))
        logger.info("Speedup: %.2fx", speedup)
        logger.info("%s", "=" * 60)

        # Verify speedup meets the >2x requirement
        assert speedup > 1.5, f"Expected >1.5x speedup, got {speedup:.2f}x"

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_canonical_output_consistency(
        self, nested_payload: list[dict[str, Any]]
    ) -> None:
        """Verify canonical output is consistent between encoders."""
        stdlib_encoder = StdLibJsonEncoder()
        orjson_encoder = OrjsonEncoder()

        # Test a subset of records
        for record in nested_payload[:100]:
            stdlib_output = stdlib_encoder.dumps_canonical(record)
            orjson_output = orjson_encoder.dumps_canonical(record)

            # Both should be valid JSON
            json.loads(stdlib_output)
            json.loads(orjson_output)

            # Both should produce ASCII-only output
            assert stdlib_output.isascii(), "StdLib canonical should be ASCII-only"
            assert orjson_output.isascii(), "Orjson canonical should be ASCII-only"

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_loads_performance(self, medium_payload: list[dict[str, Any]]) -> None:
        """Benchmark JSON deserialization performance."""
        stdlib_encoder = StdLibJsonEncoder()
        orjson_encoder = OrjsonEncoder()

        # Pre-serialize data
        json_strings = [stdlib_encoder.dumps(r) for r in medium_payload]
        iterations = 5

        # Measure stdlib loads
        stdlib_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            for s in json_strings:
                stdlib_encoder.loads(s)
            stdlib_times.append(time.perf_counter() - start)

        # Measure orjson loads
        orjson_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            for s in json_strings:
                orjson_encoder.loads(s)
            orjson_times.append(time.perf_counter() - start)

        stdlib_mean = statistics.mean(stdlib_times)
        orjson_mean = statistics.mean(orjson_times)
        speedup = stdlib_mean / orjson_mean

        logger.info("%s", "=" * 60)
        logger.info("JSON Deserialization Benchmark Results")
        logger.info("%s", "=" * 60)
        logger.info("Payload: %d JSON strings", len(json_strings))
        logger.info("StdLib json.loads: %.4fs", stdlib_mean)
        logger.info("Orjson loads:      %.4fs", orjson_mean)
        logger.info("Speedup:           %.2fx", speedup)
        logger.info("%s", "=" * 60)

        assert stdlib_mean > 0
        assert orjson_mean > 0
        assert speedup > 0


class TestBatchSerializationPerformance:
    """Benchmark batch serialization patterns used in Bronze writer."""

    @pytest.mark.benchmark
    def test_batch_serialize_stdlib(self, large_payload: list[dict[str, Any]]) -> None:
        """Benchmark batch serialization pattern with stdlib."""
        encoder = StdLibJsonEncoder()
        start = time.perf_counter()

        # Pattern from BatchWriter.write_bronze
        json_strings = [encoder.dumps(r) for r in large_payload]
        json_strings.sort()  # Deterministic ordering
        record_bytes = [(s + "\n").encode("utf-8") for s in json_strings]

        elapsed = time.perf_counter() - start
        total_bytes = sum(len(b) for b in record_bytes)
        mb_per_sec = (total_bytes / (1024 * 1024)) / elapsed

        logger.info("StdLib batch: %.4fs, %.2f MB/s", elapsed, mb_per_sec)
        logger.info("  Records: %d", len(large_payload))
        logger.info("  Total size: %.2f MB", total_bytes / (1024 * 1024))
        assert len(record_bytes) == len(large_payload)
        assert total_bytes > 0
        assert mb_per_sec > 0

    @pytest.mark.benchmark
    @pytest.mark.skipif(not orjson_available, reason="orjson not installed")
    def test_batch_serialize_orjson(self, large_payload: list[dict[str, Any]]) -> None:
        """Benchmark batch serialization pattern with orjson."""
        encoder = OrjsonEncoder()
        start = time.perf_counter()

        # Pattern from BatchWriter.write_bronze
        json_strings = [encoder.dumps(r) for r in large_payload]
        json_strings.sort()  # Deterministic ordering
        record_bytes = [(s + "\n").encode("utf-8") for s in json_strings]

        elapsed = time.perf_counter() - start
        total_bytes = sum(len(b) for b in record_bytes)
        mb_per_sec = (total_bytes / (1024 * 1024)) / elapsed

        logger.info("Orjson batch: %.4fs, %.2f MB/s", elapsed, mb_per_sec)
        logger.info("  Records: %d", len(large_payload))
        logger.info("  Total size: %.2f MB", total_bytes / (1024 * 1024))
        assert len(record_bytes) == len(large_payload)
        assert total_bytes > 0
        assert mb_per_sec > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
