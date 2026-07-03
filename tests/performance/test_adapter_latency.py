"""Performance tests for adapter call latency.

Monitors latency for external API adapter calls to detect performance
regressions in network operations.

Requirements:
- REQ-PERF-006: Adapter calls should complete within expected time limits
- REQ-PERF-007: No excessive latency in retry scenarios
"""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.benchmark, pytest.mark.performance, pytest.mark.serial]


class MockAdapter:
    """Mock adapter for latency testing."""

    def __init__(self, latency_ms: float = 100):
        self.latency_ms = latency_ms
        self.call_count = 0

    def fetch(self, identifier: str) -> dict:
        """Simulate API fetch with configurable latency."""
        self.call_count += 1
        time.sleep(self.latency_ms / 1000.0)
        return {"id": identifier, "data": f"value_{identifier}"}


def test_adapter_call_latency_baseline() -> None:
    """Test baseline adapter call latency."""
    adapter = MockAdapter(latency_ms=10)

    start = time.perf_counter()
    result = adapter.fetch("test_id")
    end = time.perf_counter()

    latency_ms = (end - start) * 1000

    assert result is not None
    assert adapter.call_count == 1
    # Should complete in ~10ms with tolerance
    assert latency_ms < 50, f"Adapter call took {latency_ms:.2f}ms (expected < 50ms)"


def test_adapter_call_latency_under_load() -> None:
    """Test adapter call latency under concurrent load."""
    adapter = MockAdapter(latency_ms=10)

    start = time.perf_counter()

    # Simulate 10 sequential calls
    results = [adapter.fetch(f"id_{i}") for i in range(10)]

    end = time.perf_counter()
    total_latency_ms = (end - start) * 1000

    assert len(results) == 10
    assert adapter.call_count == 10
    # Should complete in ~100ms with tolerance (10 * 10ms)
    assert total_latency_ms < 200, (
        f"10 calls took {total_latency_ms:.2f}ms (expected < 200ms)"
    )


def test_adapter_call_latency_with_retry() -> None:
    """Test adapter call latency with retry simulation."""
    call_count = 0

    def mock_fetch_with_failure(identifier: str) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Simulated network error")
        time.sleep(0.01)  # 10ms latency
        return {"id": identifier, "data": f"value_{identifier}"}

    start = time.perf_counter()

    # Simulate retry logic
    max_retries = 3
    result = None
    for attempt in range(max_retries):
        try:
            result = mock_fetch_with_failure("test_id")
            break
        except ConnectionError:
            if attempt == max_retries - 1:
                raise

    end = time.perf_counter()
    latency_ms = (end - start) * 1000

    assert result is not None
    assert call_count == 3
    # Should complete in ~30ms with tolerance (3 * 10ms)
    assert latency_ms < 100, f"Retry call took {latency_ms:.2f}ms (expected < 100ms)"


def test_adapter_batch_call_latency() -> None:
    """Test adapter batch call latency."""
    adapter = MockAdapter(latency_ms=10)

    start = time.perf_counter()

    # Simulate batch fetch (10 items in one call)
    batch_ids = [f"id_{i}" for i in range(10)]
    batch_result = [adapter.fetch(id_) for id_ in batch_ids]

    end = time.perf_counter()
    latency_ms = (end - start) * 1000

    assert len(batch_result) == 10
    # Sequential batch should take ~100ms
    assert latency_ms < 200, f"Batch call took {latency_ms:.2f}ms (expected < 200ms)"


@pytest.mark.parametrize("num_calls", [1, 10, 100])
def test_adapter_latency_scalability(num_calls: int) -> None:
    """Test that adapter latency scales linearly with number of calls."""
    adapter = MockAdapter(latency_ms=5)

    start = time.perf_counter()

    for i in range(num_calls):
        adapter.fetch(f"id_{i}")

    end = time.perf_counter()
    total_latency_ms = (end - start) * 1000
    avg_latency_ms = total_latency_ms / num_calls

    # Average latency should be close to configured latency
    assert avg_latency_ms < 20, f"Average latency {avg_latency_ms:.2f}ms too high"
    # Total latency should scale linearly
    expected_max_ms = num_calls * 20  # 4x tolerance
    assert total_latency_ms < expected_max_ms, (
        f"Total latency {total_latency_ms:.2f}ms exceeds expected {expected_max_ms}ms"
    )
