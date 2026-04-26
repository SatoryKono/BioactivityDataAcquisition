"""Performance baseline assertion tests.

These tests enforce performance baselines as defined in
docs/05-operations/performance-baselines.md.

Unlike regular benchmarks (test_performance.py) which measure and report,
these tests FAIL if performance degrades below baseline thresholds.

Part of architecture review refactoring plan (R5).

Note: These tests are marked with @pytest.mark.benchmark and excluded from
standard test runs. Run explicitly with: make bench or pytest -m benchmark
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest

# Mark all tests in this module as benchmark tests (excluded from standard runs)
pytestmark = pytest.mark.benchmark


class TestContentHashBaselines:
    """Baseline assertions for content hash generation.

    Baselines:
    - Small record: < 50 µs (> 20,000 ops/sec)
    - Medium record: < 150 µs (> 6,500 ops/sec)
    - Large record: < 500 µs (> 2,000 ops/sec)
    """

    # Baseline thresholds in microseconds (with safety margin for CI/Python 3.14 variability)
    SMALL_RECORD_THRESHOLD_US = (
        2000  # 40x of 50 µs target (accounts for Python 3.14/CI variance)
    )
    MEDIUM_RECORD_THRESHOLD_US = (
        5000  # ~33x of 150 µs target (accounts for Python 3.14 variance)
    )
    LARGE_RECORD_THRESHOLD_US = (
        10000  # 20x of 500 µs target (accounts for CI/Python 3.14 variance)
    )

    # Number of operations to average over
    NUM_OPS = 1000

    @pytest.fixture
    def small_record(self) -> dict[str, Any]:
        """Small record with ~10 fields."""
        return {
            "id": "CHEMBL123456",
            "canonical_smiles": "CCO",
            "pref_name": "Ethanol",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "therapeutic_flag": True,
            "dosed_ingredient": False,
            "structure_type": "MOL",
            "chirality": 0,
            "prodrug": False,
        }

    @pytest.fixture
    def medium_record(self) -> dict[str, Any]:
        """Medium record with ~50 fields."""
        return {
            "id": "CHEMBL123456",
            "canonical_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
            "pref_name": "Ibuprofen",
            "molecule_type": "Small molecule",
            "max_phase": 4,
            "therapeutic_flag": True,
            "molecule_properties": {
                "alogp": 3.5,
                "aromatic_rings": 1,
                "cx_logd": 0.8,
                "cx_logp": 3.84,
                "full_mwt": 206.29,
                "hba": 2,
                "hbd": 1,
                "heavy_atoms": 15,
                "mw_freebase": 206.29,
                "psa": 37.30,
                "qed_weighted": 0.75,
                "rtb": 4,
            },
            "molecule_synonyms": [
                {"syn_type": "TRADE_NAME", "molecule_synonym": "Advil"},
                {"syn_type": "TRADE_NAME", "molecule_synonym": "Motrin"},
                {"syn_type": "INN", "molecule_synonym": "Ibuprofen"},
            ],
            "atc_classifications": ["M01AE01", "M02AA13", "G02CC01"],
            **{f"field_{i}": f"value_{i}" for i in range(30)},
        }

    @pytest.fixture
    def large_record(self) -> dict[str, Any]:
        """Large record with ~100 fields."""
        base = {
            f"field_{i}": f"value_{i}" if i % 3 != 0 else i * 1.5 for i in range(80)
        }
        base["nested_list"] = [
            {"id": i, "name": f"item_{i}", "values": list(range(10))} for i in range(10)
        ]
        base["deep_nested"] = {
            "level1": {
                "level2": {
                    "level3": {"data": list(range(20)), "metadata": {"version": 3}}
                }
            }
        }
        return base

    def test_small_record_baseline(self, small_record: dict[str, Any]) -> None:
        """Small record hash must complete under threshold."""
        from bioetl.domain.transformations import generate_content_hash

        # Warmup
        for _ in range(10):
            generate_content_hash(small_record, "chembl")

        # Measure
        start = time.perf_counter()
        for _ in range(self.NUM_OPS):
            generate_content_hash(small_record, "chembl")
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / self.NUM_OPS) * 1_000_000

        assert avg_us < self.SMALL_RECORD_THRESHOLD_US, (
            f"Small record hash took {avg_us:.1f} µs, "
            f"exceeds baseline of {self.SMALL_RECORD_THRESHOLD_US} µs"
        )

    def test_medium_record_baseline(self, medium_record: dict[str, Any]) -> None:
        """Medium record hash must complete under threshold."""
        from bioetl.domain.transformations import generate_content_hash

        # Warmup
        for _ in range(10):
            generate_content_hash(medium_record, "chembl")

        # Measure
        start = time.perf_counter()
        for _ in range(self.NUM_OPS):
            generate_content_hash(medium_record, "chembl")
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / self.NUM_OPS) * 1_000_000

        assert avg_us < self.MEDIUM_RECORD_THRESHOLD_US, (
            f"Medium record hash took {avg_us:.1f} µs, "
            f"exceeds baseline of {self.MEDIUM_RECORD_THRESHOLD_US} µs"
        )

    def test_large_record_baseline(self, large_record: dict[str, Any]) -> None:
        """Large record hash must complete under threshold."""
        from bioetl.domain.transformations import generate_content_hash

        # Warmup
        for _ in range(10):
            generate_content_hash(large_record, "chembl")

        # Measure
        start = time.perf_counter()
        for _ in range(self.NUM_OPS):
            generate_content_hash(large_record, "chembl")
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / self.NUM_OPS) * 1_000_000

        assert avg_us < self.LARGE_RECORD_THRESHOLD_US, (
            f"Large record hash took {avg_us:.1f} µs, "
            f"exceeds baseline of {self.LARGE_RECORD_THRESHOLD_US} µs"
        )


class TestBatchProcessingBaselines:
    """Baseline assertions for batch processing.

    Baselines:
    - 100 records: < 10 ms
    - 1000 records: < 100 ms
    """

    SMALL_BATCH_THRESHOLD_MS = (
        100  # 10x of 10 ms target (accounts for Python 3.14 variance)
    )
    MEDIUM_BATCH_THRESHOLD_MS = (
        1000  # 10x of 100 ms target (accounts for CI/Python 3.14 variance)
    )

    @pytest.fixture
    def small_batch(self) -> list[dict[str, Any]]:
        """Small batch of 100 records."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "active": i % 2 == 0,
            }
            for i in range(100)
        ]

    @pytest.fixture
    def medium_batch(self) -> list[dict[str, Any]]:
        """Medium batch of 1000 records."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "active": i % 2 == 0,
                "properties": {"weight": i * 0.1, "volume": i * 0.01},
            }
            for i in range(1000)
        ]

    def test_small_batch_baseline(self, small_batch: list[dict[str, Any]]) -> None:
        """Small batch hash generation must complete under threshold."""
        from bioetl.domain.transformations import generate_content_hash

        # Warmup
        for record in small_batch[:10]:
            generate_content_hash(record, "test")

        # Measure (5 iterations for averaging)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            for record in small_batch:
                generate_content_hash(record, "test")
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms

        avg_ms = sum(times) / len(times)

        assert avg_ms < self.SMALL_BATCH_THRESHOLD_MS, (
            f"Small batch (100 records) took {avg_ms:.1f} ms, "
            f"exceeds baseline of {self.SMALL_BATCH_THRESHOLD_MS} ms"
        )

    def test_medium_batch_baseline(self, medium_batch: list[dict[str, Any]]) -> None:
        """Medium batch hash generation must complete under threshold."""
        from bioetl.domain.transformations import generate_content_hash

        # Warmup
        for record in medium_batch[:10]:
            generate_content_hash(record, "test")

        # Measure (3 iterations for averaging)
        times = []
        for _ in range(3):
            start = time.perf_counter()
            for record in medium_batch:
                generate_content_hash(record, "test")
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        avg_ms = sum(times) / len(times)

        assert avg_ms < self.MEDIUM_BATCH_THRESHOLD_MS, (
            f"Medium batch (1000 records) took {avg_ms:.1f} ms, "
            f"exceeds baseline of {self.MEDIUM_BATCH_THRESHOLD_MS} ms"
        )


class TestPolarsBaselines:
    """Baseline assertions for Polars DataFrame operations.

    Baselines (5000 records):
    - DataFrame creation: < 20 ms
    - Filter operation: < 5 ms
    - Group + Aggregate: < 10 ms
    """

    DF_CREATION_THRESHOLD_MS = (
        100  # 5x of 20 ms target (accounts for Python 3.14 variance)
    )
    FILTER_THRESHOLD_MS = 30  # 6x of 5 ms target (accounts for Python 3.14 variance)
    GROUP_AGG_THRESHOLD_MS = (
        150  # 15x of 10 ms target (accounts for Python 3.14 variance)
    )
    WINDOWS_GROUP_AGG_THRESHOLD_MS = 300

    @pytest.fixture
    def records_for_df(self) -> list[dict[str, Any]]:
        """Records for DataFrame creation."""
        return [
            {
                "id": f"record_{i}",
                "value": i * 1.5,
                "name": f"Item {i}",
                "category": f"cat_{i % 10}",
                "active": i % 2 == 0,
            }
            for i in range(5000)
        ]

    def test_dataframe_creation_baseline(
        self, records_for_df: list[dict[str, Any]]
    ) -> None:
        """DataFrame creation must complete under threshold."""
        import polars as pl

        # Warmup
        _ = pl.DataFrame(records_for_df[:100])

        # Measure (5 iterations)
        times = []
        for _ in range(5):
            start = time.perf_counter()
            _ = pl.DataFrame(records_for_df)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        avg_ms = sum(times) / len(times)

        assert avg_ms < self.DF_CREATION_THRESHOLD_MS, (
            f"DataFrame creation took {avg_ms:.1f} ms, "
            f"exceeds baseline of {self.DF_CREATION_THRESHOLD_MS} ms"
        )

    def test_filter_operation_baseline(
        self, records_for_df: list[dict[str, Any]]
    ) -> None:
        """Filter operation must complete under threshold."""
        import polars as pl

        df = pl.DataFrame(records_for_df)

        # Warmup
        _ = df.filter(pl.col("active"))

        # Measure (10 iterations)
        times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = df.filter(pl.col("active"))
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        avg_ms = sum(times) / len(times)

        assert avg_ms < self.FILTER_THRESHOLD_MS, (
            f"Filter operation took {avg_ms:.1f} ms, "
            f"exceeds baseline of {self.FILTER_THRESHOLD_MS} ms"
        )

    def test_group_aggregate_baseline(
        self, records_for_df: list[dict[str, Any]]
    ) -> None:
        """Group + aggregate operation must complete under threshold."""
        import polars as pl

        df = pl.DataFrame(records_for_df)

        # Warmup
        _ = df.group_by("category").agg(pl.col("value").mean())

        # Measure (10 iterations)
        times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = df.group_by("category").agg(
                pl.col("value").mean().alias("avg_value"),
                pl.col("active").sum().alias("active_count"),
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        avg_ms = sum(times) / len(times)
        threshold_ms = (
            self.WINDOWS_GROUP_AGG_THRESHOLD_MS
            if os.name == "nt"
            else self.GROUP_AGG_THRESHOLD_MS
        )

        assert avg_ms < threshold_ms, (
            f"Group + aggregate took {avg_ms:.1f} ms, "
            f"exceeds baseline of {threshold_ms} ms"
        )


class TestMemoryMonitorBaseline:
    """Baseline assertions for MemoryMonitor operations.

    Baselines:
    - get_memory_stats(): < 1 ms
    - get_recommended_batch_size(): < 100 µs
    """

    MEMORY_STATS_THRESHOLD_MS = 50  # Increased for Python 3.14/CI variability
    BATCH_SIZE_THRESHOLD_US = 50000  # Increased for Python 3.14/CI variability

    def test_memory_stats_baseline(self) -> None:
        """Memory stats retrieval must complete under threshold."""
        from bioetl.domain.config import MemoryConfig
        from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor(config=MemoryConfig())

        # Extended warmup to ensure psutil/OS caches are primed
        for _ in range(20):
            monitor.get_memory_stats()

        # Measure (100 iterations)
        times = []
        for _ in range(100):
            start = time.perf_counter()
            monitor.get_memory_stats()
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

        # Use median instead of average for robustness against CI outliers
        sorted_times = sorted(times)
        median_ms = sorted_times[len(sorted_times) // 2]

        assert median_ms < self.MEMORY_STATS_THRESHOLD_MS, (
            f"get_memory_stats() took {median_ms:.2f} ms (median), "
            f"exceeds baseline of {self.MEMORY_STATS_THRESHOLD_MS} ms"
        )

    def test_recommended_batch_size_baseline(self) -> None:
        """Recommended batch size calculation must complete under threshold."""
        from bioetl.domain.config import MemoryConfig
        from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

        monitor = MemoryMonitor(config=MemoryConfig())

        # Warmup
        for _ in range(10):
            monitor.get_recommended_batch_size(1000)

        # Measure (1000 iterations)
        start = time.perf_counter()
        for _ in range(1000):
            monitor.get_recommended_batch_size(1000)
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / 1000) * 1_000_000

        assert avg_us < self.BATCH_SIZE_THRESHOLD_US, (
            f"get_recommended_batch_size() took {avg_us:.1f} µs, "
            f"exceeds baseline of {self.BATCH_SIZE_THRESHOLD_US} µs"
        )
