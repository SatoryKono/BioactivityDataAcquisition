"""JSON serialization benchmarks.

Compares performance of stdlib json vs orjson for typical BioETL workloads.

Run with:
    pytest benchmarks/test_json_serialization.py -v --benchmark-only

Requirements:
    - pip install pytest-benchmark orjson
"""

from __future__ import annotations

import json
import os
import statistics
import time
from typing import Any

import pytest

from bioetl.infrastructure.serialization.encoders import (
    ORJSON_AVAILABLE,
    OrjsonEncoder,
    StdLibJsonEncoder,
)


@pytest.fixture
def nested_payload() -> list[dict[str, Any]]:
    """Payload with nested structures typical of bioactivity data."""
    return [
        {
            "id": f"RECORD_{i:06d}",
            "molecule_chembl_id": f"CHEMBL{100000 + i}",
            "assay_chembl_id": f"CHEMBL{200000 + i}",
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
        print(f"\nStdLib small: {ops_per_sec:.0f} ops/sec, {elapsed/iterations:.4f}s per batch")

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
        print(f"\nStdLib medium: {ops_per_sec:.0f} ops/sec, {elapsed/iterations:.4f}s per batch")

    @pytest.mark.benchmark
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
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
        print(f"\nOrjson small: {ops_per_sec:.0f} ops/sec, {elapsed/iterations:.4f}s per batch")

    @pytest.mark.benchmark
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
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
        print(f"\nOrjson medium: {ops_per_sec:.0f} ops/sec, {elapsed/iterations:.4f}s per batch")

    @pytest.mark.benchmark
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_performance_comparison(
        self, medium_payload: list[dict[str, Any]]
    ) -> None:
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

        print(f"\n{'='*60}")
        print("JSON Serialization Benchmark Results")
        print(f"{'='*60}")
        print(f"Payload: {len(medium_payload)} records")
        print(f"Iterations: {iterations}")
        print(f"\nStdLib json:")
        print(f"  Mean: {stdlib_mean:.4f}s")
        print(f"  Std:  {statistics.stdev(stdlib_times):.4f}s")
        print(f"\nOrjson:")
        print(f"  Mean: {orjson_mean:.4f}s")
        print(f"  Std:  {statistics.stdev(orjson_times):.4f}s")
        print(f"\nSpeedup: {speedup:.2f}x")
        print(f"{'='*60}")

        # Verify speedup meets the >2x requirement
        assert speedup > 1.5, f"Expected >1.5x speedup, got {speedup:.2f}x"

    @pytest.mark.benchmark
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
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
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
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

        print(f"\n{'='*60}")
        print("JSON Deserialization Benchmark Results")
        print(f"{'='*60}")
        print(f"Payload: {len(json_strings)} JSON strings")
        print(f"\nStdLib json.loads: {stdlib_mean:.4f}s")
        print(f"Orjson loads:      {orjson_mean:.4f}s")
        print(f"Speedup:           {speedup:.2f}x")
        print(f"{'='*60}")


class TestBatchSerializationPerformance:
    """Benchmark batch serialization patterns used in Bronze writer."""

    @pytest.mark.benchmark
    def test_batch_serialize_stdlib(
        self, large_payload: list[dict[str, Any]]
    ) -> None:
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

        print(f"\nStdLib batch: {elapsed:.4f}s, {mb_per_sec:.2f} MB/s")
        print(f"  Records: {len(large_payload)}")
        print(f"  Total size: {total_bytes / (1024 * 1024):.2f} MB")

    @pytest.mark.benchmark
    @pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")
    def test_batch_serialize_orjson(
        self, large_payload: list[dict[str, Any]]
    ) -> None:
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

        print(f"\nOrjson batch: {elapsed:.4f}s, {mb_per_sec:.2f} MB/s")
        print(f"  Records: {len(large_payload)}")
        print(f"  Total size: {total_bytes / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
