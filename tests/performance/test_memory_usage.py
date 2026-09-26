"""Performance tests for memory usage.

Monitors memory consumption for large datasets to detect memory leaks
and excessive memory usage patterns.

Requirements:
- Memory usage should be linear with dataset size
- No memory leaks in long-running operations
"""

from __future__ import annotations

import gc
import subprocess
import sys
import tracemalloc

import pytest
import polars as pl

pytestmark = [pytest.mark.benchmark, pytest.mark.performance, pytest.mark.serial]


@pytest.fixture
def memory_tracker():
    """Context manager for tracking memory usage."""
    tracemalloc.start()
    current, peak = tracemalloc.get_traced_memory()
    yield {
        "start_current": current,
        "start_peak": peak,
    }
    tracemalloc.stop()


def test_memory_usage_dataframe_creation(memory_tracker: dict[str, int]) -> None:
    """Test memory usage for DataFrame creation scales linearly."""
    sizes = [100, 1000, 10000]
    memory_snapshots = []

    for size in sizes:
        gc.collect()  # Force garbage collection before measurement

        data = {
            "id": list(range(size)),
            "value": [float(i) for i in range(size)],
            "name": [f"item_{i}" for i in range(size)],
        }

        df = pl.DataFrame(data)

        current, peak = tracemalloc.get_traced_memory()
        memory_snapshots.append(
            {
                "size": size,
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024,
            }
        )

        del df
        gc.collect()

    # Check that memory usage scales roughly linearly
    # Allow 2x tolerance for overhead
    ratio_100_1000 = memory_snapshots[1]["peak_mb"] / memory_snapshots[0]["peak_mb"]
    ratio_1000_10000 = memory_snapshots[2]["peak_mb"] / memory_snapshots[1]["peak_mb"]

    assert ratio_100_1000 < 20, (
        f"Memory usage scaling 100->1000: {ratio_100_1000:.2f}x (expected ~10x)"
    )
    assert ratio_1000_10000 < 20, (
        f"Memory usage scaling 1000->10000: {ratio_1000_10000:.2f}x (expected ~10x)"
    )


def test_memory_usage_no_leak_in_repeated_operations() -> None:
    """Test that repeated operations don't leak memory."""
    # Hypothesis registers GC callbacks that can stall Polars collect under
    # full-suite memory pressure on Windows; isolate measurement from those
    # callbacks without changing the leak-detection contract.
    saved_gc_callbacks = gc.callbacks[:]
    gc.callbacks.clear()
    try:
        tracemalloc.start()
        gc.collect()

        initial_current, initial_peak = tracemalloc.get_traced_memory()

        # Perform operation 100 times
        for _ in range(100):
            data = {
                "id": list(range(100)),
                "value": [float(j) for j in range(100)],
            }
            df = pl.DataFrame(data)

            # Do some operation
            result = df.filter(pl.col("value") > 50)

            del df, result

        gc.collect()
        final_current, final_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    finally:
        gc.callbacks[:] = saved_gc_callbacks

    # Memory should not grow significantly (allow 10x tolerance for overhead)
    current_growth = (final_current - initial_current) / 1024 / 1024
    peak_growth = (final_peak - initial_peak) / 1024 / 1024

    assert current_growth < 50, (
        f"Current memory grew by {current_growth:.2f} MB (possible leak)"
    )
    assert peak_growth < 100, (
        f"Peak memory grew by {peak_growth:.2f} MB (possible leak)"
    )


def test_process_memory_limits() -> None:
    """Test that process memory usage is within reasonable limits."""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import polars, psutil; print(psutil.Process().memory_info().rss)",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    rss_mb = int(completed.stdout.strip()) / 1024 / 1024

    # Process should use less than 2GB for idle state
    assert rss_mb < 2048, f"Process using too much memory: {rss_mb:.2f} MB"


@pytest.mark.parametrize("batch_size", [100, 1000, 5000])
def test_memory_usage_per_batch(batch_size: int) -> None:
    """Test memory usage per batch operation."""
    tracemalloc.start()
    gc.collect()

    initial_current, initial_peak = tracemalloc.get_traced_memory()

    # Create batch
    data = {
        "id": list(range(batch_size)),
        "value": [float(i) for i in range(batch_size)],
        "text": [f"text_{i}" * 10 for i in range(batch_size)],
    }
    df = pl.DataFrame(data)

    # Perform typical operations
    filtered = df.filter(pl.col("value") > batch_size / 2)
    grouped = filtered.group_by("id").agg(pl.col("value").mean())

    final_current, final_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_per_record_mb = (final_peak - initial_peak) / batch_size / 1024 / 1024

    # Should use less than 1KB per record (adjust based on actual data)
    assert memory_per_record_mb < 0.001, (
        f"Memory per record too high: {memory_per_record_mb * 1024:.2f} KB"
    )

    del df, filtered, grouped
    gc.collect()
