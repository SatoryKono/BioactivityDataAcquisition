"""Tests for PipelineRegistry thread safety.

Verifies that registry operations are thread-safe as per CLAUDE.md requirements.
Tests concurrent access patterns that could expose race conditions.

Updated for instance-level PipelineRegistry (2025-12).
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.factories.pipeline.registry import register_all_pipelines

if TYPE_CHECKING:
    from bioetl.domain.ports import PipelineFactoryPort


def create_mock_factory(name: str) -> PipelineFactoryPort:
    """Create a mock factory for testing.

    Args:
        name: Pipeline name for the factory.

    Returns:
        Mock factory implementing PipelineFactoryPort.
    """
    factory = MagicMock()
    factory.pipeline_name = name
    factory.silver_schema = pa.schema([("id", pa.int64())])
    factory.gold_schema = MagicMock()  # Non-None gold_schema required
    return factory


class TestConcurrentRegistration:
    """Tests for concurrent registration safety."""

    def test_concurrent_registration_from_multiple_threads(
        self, isolated_registry
    ) -> None:
        """10 threads registering different factories simultaneously.

        Verifies that no race conditions occur during concurrent writes.
        """
        num_threads = 10
        results: list[tuple[str, bool]] = []

        def register_factory(idx: int) -> None:
            """Register a factory with unique name."""
            factory = create_mock_factory(f"test_pipeline_{idx}")
            isolated_registry.register_factory(factory)
            results.append((f"test_pipeline_{idx}", True))

        # Execute all registrations concurrently
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(register_factory, i) for i in range(num_threads)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        # Verify all registrations succeeded
        assert len(results) == num_threads, (
            f"Expected {num_threads} registrations, got {len(results)}"
        )

        # Verify all pipelines are registered
        registered = isolated_registry.list_pipelines()
        for i in range(num_threads):
            assert f"test_pipeline_{i}" in registered, (
                f"Pipeline test_pipeline_{i} not found in registry"
            )

    def test_concurrent_read_write_safety(self, isolated_registry) -> None:
        """Concurrent reads during writes do not cause errors.

        Simulates real-world scenario where list_pipelines() is called
        while register_factory() is in progress.
        """
        num_writers = 5
        num_readers = 10
        read_results: list[list[str]] = []

        def writer(idx: int) -> None:
            """Register a factory."""
            try:
                factory = create_mock_factory(f"concurrent_pipeline_{idx}")
                isolated_registry.register_factory(factory)
            except ValueError:
                # Already registered - expected in some race scenarios
                pass

        def reader() -> None:
            """Read the registry."""
            # Small delay to interleave with writes
            time.sleep(0.001)
            result = isolated_registry.list_pipelines()
            read_results.append(result)

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
        # Verify all reads returned valid lists
        for result in read_results:
            assert isinstance(result, list), "list_pipelines() must return a list"

    def test_double_registration_raises_error(self, isolated_registry) -> None:
        """Registering the same pipeline twice raises ValueError.

        Ensures duplicate detection works correctly.
        """
        factory = create_mock_factory("duplicate_pipeline")

        # First registration succeeds
        isolated_registry.register_factory(factory)

        # Second registration fails
        with pytest.raises(ValueError, match="Pipeline already registered"):
            isolated_registry.register_factory(factory)

    def test_double_registration_concurrent(self, isolated_registry) -> None:
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
                isolated_registry.register_factory(factory)
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

    def test_list_pipelines_returns_sorted_list(self, isolated_registry) -> None:
        """list_pipelines() returns alphabetically sorted list.

        Ensures deterministic ordering regardless of registration order.
        """
        # Register in non-alphabetical order
        names = ["zebra", "alpha", "mike", "beta"]
        for name in names:
            factory = create_mock_factory(name)
            isolated_registry.register_factory(factory)

        result = isolated_registry.list_pipelines()

        # Verify sorted order
        assert result == sorted(names), (
            f"Expected sorted list {sorted(names)}, got {result}"
        )

    def test_list_pipelines_consistent_across_calls(self, isolated_registry) -> None:
        """Multiple calls to list_pipelines() return identical results.

        Verifies no random ordering or side effects.
        """
        # Register some pipelines
        for name in ["pipeline_a", "pipeline_b", "pipeline_c"]:
            factory = create_mock_factory(name)
            isolated_registry.register_factory(factory)

        # Call multiple times
        results = [isolated_registry.list_pipelines() for _ in range(10)]

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "list_pipelines() results are not consistent"


class TestRegisterAllPipelinesThreadSafety:
    """Tests for register_all_pipelines() thread safety."""

    def test_concurrent_register_all_pipelines_idempotent(
        self, isolated_registry
    ) -> None:
        """Multiple threads calling register_all_pipelines() with same registry.

        Since we're using an isolated registry and passing it explicitly,
        all calls will register to the same instance.
        """
        num_threads = 10
        call_count = []
        lock = threading.Lock()
        barrier = threading.Barrier(num_threads)

        def call_register() -> None:
            """Call register_all_pipelines()."""
            barrier.wait()
            try:
                # First call will register, subsequent calls should fail
                # since the registry already has the pipelines
                register_all_pipelines(registry=isolated_registry)
            except ValueError:
                # Expected for duplicate registrations
                pass
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

    def test_multiple_registries_parallel(self) -> None:
        """Multiple isolated registries can be populated in parallel."""
        num_registries = 5
        registries: list[PipelineRegistry] = []

        def populate_registry() -> PipelineRegistry:
            """Create and populate a registry."""
            registry = create_registry()
            register_all_pipelines(registry=registry)
            return registry

        with ThreadPoolExecutor(max_workers=num_registries) as executor:
            futures = [
                executor.submit(populate_registry) for _ in range(num_registries)
            ]
            for future in as_completed(futures):
                registries.append(future.result())

        # All registries should be populated
        assert len(registries) == num_registries

        # All registries should have same pipelines
        first_pipelines = registries[0].list_pipelines()
        for registry in registries[1:]:
            assert registry.list_pipelines() == first_pipelines

        # But all registries should be different instances
        for i, registry1 in enumerate(registries):
            for j, registry2 in enumerate(registries):
                if i != j:
                    assert registry1 is not registry2


class TestRegistryLockBehavior:
    """Tests for RLock reentrant behavior."""

    def test_contains_after_list_pipelines(self, isolated_registry) -> None:
        """Sequential calls using lock don't deadlock.

        RLock allows reentrant access from same thread.
        """
        factory = create_mock_factory("reentrant_test")
        isolated_registry.register_factory(factory)

        # These operations use the same lock internally
        pipelines = isolated_registry.list_pipelines()
        for name in pipelines:
            # contains() also uses the lock
            assert isolated_registry.contains(name)

    def test_get_after_contains(self, isolated_registry) -> None:
        """get() works after contains() check.

        Verifies no lock issues with consecutive operations.
        """
        factory = create_mock_factory("get_test")
        isolated_registry.register_factory(factory)

        if isolated_registry.contains("get_test"):
            definition = isolated_registry.get("get_test")
            assert definition.factory.pipeline_name == "get_test"
