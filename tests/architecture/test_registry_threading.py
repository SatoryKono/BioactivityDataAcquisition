"""Tests for PipelineRegistry thread safety.

Verifies that registry operations are thread-safe as per CLAUDE.md requirements.
Tests concurrent access patterns that could expose race conditions.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.factories.pipeline_factories import (
    register_all_pipelines,
    reset_registration,
)
from bioetl.composition.registry import PipelineRegistry

if TYPE_CHECKING:
    from bioetl.composition.registry import PipelineFactoryProtocol


def create_mock_factory(name: str) -> PipelineFactoryProtocol:
    """Create a mock factory for testing.

    Args:
        name: Pipeline name for the factory.

    Returns:
        Mock factory implementing PipelineFactoryProtocol.
    """
    factory = MagicMock()
    factory.pipeline_name = name
    factory.silver_schema = pa.schema([("id", pa.int64())])
    factory.gold_schema = MagicMock()  # Non-None gold_schema required
    return factory


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before and after each test."""
    reset_registration()
    yield
    reset_registration()


class TestConcurrentRegistration:
    """Tests for concurrent registration safety."""

    def test_concurrent_registration_from_multiple_threads(self) -> None:
        """10 threads registering different factories simultaneously.

        Verifies that no race conditions occur during concurrent writes.
        """
        num_threads = 10
        results: list[tuple[str, bool]] = []
        errors: list[Exception] = []

        def register_factory(idx: int) -> None:
            """Register a factory with unique name."""
            try:
                factory = create_mock_factory(f"test_pipeline_{idx}")
                PipelineRegistry.register_factory(factory)
                results.append((f"test_pipeline_{idx}", True))
            except Exception as e:
                errors.append(e)

        # Execute all registrations concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_factory, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        # Verify all registrations succeeded
        assert len(errors) == 0, f"Errors during registration: {errors}"
        assert len(results) == num_threads, (
            f"Expected {num_threads} registrations, got {len(results)}"
        )

        # Verify all pipelines are registered
        registered = PipelineRegistry.list_pipelines()
        for i in range(num_threads):
            assert f"test_pipeline_{i}" in registered, (
                f"Pipeline test_pipeline_{i} not found in registry"
            )

    def test_concurrent_read_write_safety(self) -> None:
        """Concurrent reads during writes do not cause errors.

        Simulates real-world scenario where list_pipelines() is called
        while register_factory() is in progress.
        """
        num_writers = 5
        num_readers = 10
        read_results: list[list[str]] = []
        errors: list[Exception] = []

        def writer(idx: int) -> None:
            """Register a factory."""
            try:
                factory = create_mock_factory(f"concurrent_pipeline_{idx}")
                PipelineRegistry.register_factory(factory)
            except ValueError:
                # Already registered - expected in some race scenarios
                pass
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            """Read the registry."""
            try:
                # Small delay to interleave with writes
                time.sleep(0.001)
                result = PipelineRegistry.list_pipelines()
                read_results.append(result)
            except Exception as e:
                errors.append(e)

        # Mix readers and writers
        with ThreadPoolExecutor(max_workers=num_writers + num_readers) as executor:
            futures = []
            for i in range(num_writers):
                futures.append(executor.submit(writer, i))
            for _ in range(num_readers):
                futures.append(executor.submit(reader))

            for future in as_completed(futures):
                future.result()

        # Verify no errors during concurrent access
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"

        # Verify all reads returned valid lists
        for result in read_results:
            assert isinstance(result, list), "list_pipelines() must return a list"

    def test_double_registration_raises_error(self) -> None:
        """Registering the same pipeline twice raises ValueError.

        Ensures duplicate detection works correctly.
        """
        factory = create_mock_factory("duplicate_pipeline")

        # First registration succeeds
        PipelineRegistry.register_factory(factory)

        # Second registration fails
        with pytest.raises(ValueError, match="Pipeline already registered"):
            PipelineRegistry.register_factory(factory)

    def test_double_registration_concurrent(self) -> None:
        """Concurrent attempts to register same pipeline.

        Only one should succeed, others should get ValueError.
        """
        num_threads = 10
        successes = []
        failures = []
        barrier = threading.Barrier(num_threads)

        def try_register(idx: int) -> None:
            """Try to register the same factory."""
            factory = create_mock_factory("same_pipeline")
            # Synchronize all threads to start at the same time
            barrier.wait()
            try:
                PipelineRegistry.register_factory(factory)
                successes.append(idx)
            except ValueError:
                failures.append(idx)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_register, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        # Exactly one should succeed
        assert len(successes) == 1, (
            f"Expected 1 success, got {len(successes)}: {successes}"
        )
        assert len(failures) == num_threads - 1, (
            f"Expected {num_threads - 1} failures, got {len(failures)}"
        )


class TestListPipelinesDeterminism:
    """Tests for deterministic list_pipelines() behavior."""

    def test_list_pipelines_returns_sorted_list(self) -> None:
        """list_pipelines() returns alphabetically sorted list.

        Ensures deterministic ordering regardless of registration order.
        """
        # Register in non-alphabetical order
        names = ["zebra", "alpha", "mike", "beta"]
        for name in names:
            factory = create_mock_factory(name)
            PipelineRegistry.register_factory(factory)

        result = PipelineRegistry.list_pipelines()

        # Verify sorted order
        assert result == sorted(names), (
            f"Expected sorted list {sorted(names)}, got {result}"
        )

    def test_list_pipelines_consistent_across_calls(self) -> None:
        """Multiple calls to list_pipelines() return identical results.

        Verifies no random ordering or side effects.
        """
        # Register some pipelines
        for name in ["pipeline_a", "pipeline_b", "pipeline_c"]:
            factory = create_mock_factory(name)
            PipelineRegistry.register_factory(factory)

        # Call multiple times
        results = [PipelineRegistry.list_pipelines() for _ in range(10)]

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, (
                "list_pipelines() results are not consistent"
            )


class TestRegisterAllPipelinesThreadSafety:
    """Tests for register_all_pipelines() thread safety."""

    def test_concurrent_register_all_pipelines_idempotent(self) -> None:
        """Multiple threads calling register_all_pipelines() simultaneously.

        Only one should perform registration, others should return immediately.
        """
        num_threads = 10
        call_count = []
        lock = threading.Lock()
        barrier = threading.Barrier(num_threads)

        def call_register() -> None:
            """Call register_all_pipelines()."""
            barrier.wait()
            register_all_pipelines()
            with lock:
                call_count.append(1)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(call_register) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        # All threads should complete
        assert len(call_count) == num_threads, (
            f"Expected {num_threads} completions, got {len(call_count)}"
        )

        # Registry should have correct pipelines
        registered = PipelineRegistry.list_pipelines()
        assert len(registered) > 0, "No pipelines registered"

        # Call again - should be idempotent
        initial_count = len(registered)
        register_all_pipelines()
        assert len(PipelineRegistry.list_pipelines()) == initial_count, (
            "register_all_pipelines() is not idempotent"
        )


class TestRegistryLockBehavior:
    """Tests for RLock reentrant behavior."""

    def test_contains_after_list_pipelines(self) -> None:
        """Sequential calls using lock don't deadlock.

        RLock allows reentrant access from same thread.
        """
        factory = create_mock_factory("reentrant_test")
        PipelineRegistry.register_factory(factory)

        # These operations use the same lock internally
        pipelines = PipelineRegistry.list_pipelines()
        for name in pipelines:
            # contains() also uses the lock
            assert PipelineRegistry.contains(name)

    def test_get_after_contains(self) -> None:
        """get() works after contains() check.

        Verifies no lock issues with consecutive operations.
        """
        factory = create_mock_factory("get_test")
        PipelineRegistry.register_factory(factory)

        if PipelineRegistry.contains("get_test"):
            definition = PipelineRegistry.get("get_test")
            assert definition.factory.pipeline_name == "get_test"
